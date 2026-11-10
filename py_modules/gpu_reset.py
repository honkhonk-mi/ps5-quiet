"""PS5 hot-idle workaround, loaded by Decky from py_modules.

Never writes fan, maximum-frequency or CPU controls.
"""
import fcntl
import json
import os
import threading
import time
from pathlib import Path


class ResetError(RuntimeError):
    pass


class GPUReset:
    def __init__(self, runtime, gpu='/sys/class/devfreq/ps5-gpufreq',
                 hwmon='/sys/class/hwmon', sleep=time.sleep,
                 boot_id='/proc/sys/kernel/random/boot_id'):
        self.runtime, self.gpu, self.hwmon = Path(runtime), Path(gpu), Path(hwmon)
        self.boot_id, self.sleep = Path(boot_id), sleep
        self.guard = threading.Lock()
        self.last_finished = 0.0
        self.runtime.mkdir(parents=True, exist_ok=True)

    def _read(self, name):
        return int((self.gpu / name).read_text().strip())

    def _frequencies(self):
        return sorted({int(x) for x in
                       (self.gpu / 'available_frequencies').read_text().split()
                       if x.isdigit() and int(x) > 0})

    def _effective(self, value):
        return value or self._frequencies()[0]

    def _write_min(self, value):
        (self.gpu / 'min_freq').write_text(str(value))

    def _save(self, name, value):
        target = self.runtime / name
        temp = target.with_suffix('.tmp')
        with temp.open('w') as f:
            os.chmod(temp, 0o600)
            json.dump(value, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, target)

    def _pending(self):
        return self.runtime / 'pending.json'

    def _lock(self):
        handle = (self.runtime / 'reset.lock').open('a')
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            raise ResetError('Сброс уже выполняется. Подождите несколько секунд.')
        return handle

    def _restore_pending(self):
        pending = self._pending()
        if not pending.exists():
            return False
        state = json.loads(pending.read_text())
        if state.get('boot_id') != self.boot_id.read_text().strip():
            pending.unlink()
            return False
        original, pulse = state.get('original_min'), state.get('pulse')
        frequencies = self._frequencies()
        if (type(original) is not int or type(pulse) is not int or
                original < 0 or original > frequencies[-1] or pulse not in frequencies):
            raise ResetError('Повреждены данные возврата частоты. Сброс остановлен.')
        current = self._read('min_freq')
        if current == pulse:
            maximum = self._read('max_freq') or frequencies[-1]
            if self._effective(original) > maximum:
                raise ResetError('Лимит GPU изменился. Не удалось вернуть прежний минимум.')
            self._write_min(original)
            if self._effective(self._read('min_freq')) != self._effective(original):
                raise ResetError('Драйвер не подтвердил возврат частоты GPU.')
        elif self._effective(current) != self._effective(original):
            # A different controller changed the minimum: its setting wins.
            pending.unlink()
            raise ResetError('Настройки GPU изменило другое приложение. Его значение сохранено.')
        pending.unlink()
        return True

    def recover(self):
        with self.guard, self._lock():
            return self._restore_pending()

    def status(self):
        result = {'supported': False, 'ready': False, 'reason': None,
                  'temperature_c': None, 'fan_percent': None,
                  'frequency_mhz': None, 'cooldown_seconds': 0}
        for directory in sorted(self.hwmon.glob('hwmon*')):
            try:
                name = (directory / 'name').read_text().strip()
                if name == 'k10temp':
                    result['temperature_c'] = round(int((directory / 'temp1_input').read_text()) / 1000, 1)
                elif name == 'ps5_fan':
                    result['fan_percent'] = round(int((directory / 'pwm1').read_text()) * 100 / 255)
            except (OSError, ValueError):
                continue
        try:
            if (self.gpu / 'name').read_text().strip() != 'ps5-gpufreq':
                raise ValueError('not a PS5 GPU')
            frequencies = self._frequencies()
            low, high, current = (self._read(n) for n in ('min_freq', 'max_freq', 'cur_freq'))
            pulse = next((f for f in frequencies if (low or frequencies[0]) < f <= (high or frequencies[-1])), None)
            result.update(supported=True, frequency_mhz=round(current / 1_000_000),
                          minimum_hz=low, maximum_hz=high, pulse_hz=pulse)
            cooldown = max(0, 10 - (time.monotonic() - self.last_finished)) if self.last_finished else 0
            result['cooldown_seconds'] = int(cooldown + 0.99)
            if self.guard.locked():
                result['reason'] = 'Сброс выполняется…'
            elif pulse is None:
                result['reason'] = 'Частота GPU зафиксирована. Верните автоматический режим в PS5 Hardware Control.'
            elif current > (low or frequencies[0]) + 25_000_000:
                result['reason'] = 'GPU под нагрузкой. Закройте игру и повторите в меню Steam.'
            elif cooldown > 0:
                result['reason'] = 'Можно повторить через несколько секунд.'
            else:
                result['ready'] = True
        except (OSError, ValueError, IndexError):
            result['reason'] = 'Управление GPU этой PS5 недоступно.'
        try:
            result['last_reset'] = json.loads((self.runtime / 'last.json').read_text())
        except (OSError, ValueError):
            result['last_reset'] = None
        return result

    def reset(self):
        if not self.guard.acquire(blocking=False):
            raise ResetError('Сброс уже выполняется.')
        try:
            with self._lock():
                self._restore_pending()
                if (self.gpu / 'name').read_text().strip() != 'ps5-gpufreq':
                    raise ResetError('Это не поддерживаемый GPU PS5.')
                frequencies = self._frequencies()
                original, maximum, current = (self._read(n) for n in ('min_freq', 'max_freq', 'cur_freq'))
                minimum = original or frequencies[0]
                pulse = next((f for f in frequencies if minimum < f <= (maximum or frequencies[-1])), None)
                if pulse is None:
                    raise ResetError('Частота GPU зафиксирована. Верните автоматический режим.')
                if current > minimum + 25_000_000:
                    raise ResetError('GPU под нагрузкой. Закройте игру и повторите в меню Steam.')
                if self.last_finished and time.monotonic() - self.last_finished < 10:
                    raise ResetError('Подождите несколько секунд перед повторным сбросом.')
                state = {'boot_id': self.boot_id.read_text().strip(), 'original_min': original,
                         'pulse': pulse, 'original_max': maximum, 'time': int(time.time())}
                self._save('pending.json', state)
                try:
                    self._write_min(pulse)
                    if self._read('min_freq') != pulse:
                        raise ResetError('Драйвер не подтвердил временную частоту GPU.')
                    self.sleep(2.0)
                finally:
                    self._restore_pending()
                self.last_finished = time.monotonic()
                state.update(restored=True, finished=int(time.time()))
                self._save('last.json', state)
                return state
        finally:
            self.guard.release()
