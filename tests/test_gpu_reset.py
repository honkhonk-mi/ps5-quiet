import fcntl
import json
import tempfile
import unittest
from pathlib import Path

from gpu_reset import GPUReset, ResetError


class GPUResetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.gpu = self.base / 'gpu'
        self.gpu.mkdir()
        for key, value in {'name': 'ps5-gpufreq', 'min_freq': '500000000',
                           'max_freq': '2230000000', 'cur_freq': '500000000',
                           'available_frequencies': '500000000 625000000 750000000 2230000000',
                           'governor': 'simple_ondemand'}.items():
            (self.gpu / key).write_text(value)
        self.boot = self.base / 'boot_id'
        self.boot.write_text('boot-one')
        self.hwmon = self.base / 'hwmon'
        for directory, name, values in [('hwmon0', 'ps5_fan', {'pwm1': '107'}),
                                         ('hwmon1', 'k10temp', {'temp1_input': '62500'})]:
            d = self.hwmon / directory
            d.mkdir(parents=True)
            (d / 'name').write_text(name)
            for k, v in values.items():
                (d / k).write_text(v)
        self.controller = self.new_controller(lambda seconds: None)

    def new_controller(self, sleep):
        return GPUReset(self.base / 'runtime', self.gpu, self.hwmon, sleep, self.boot)

    def minimum(self):
        return int((self.gpu / 'min_freq').read_text())

    def test_pulse_restores_limits_without_touching_fan(self):
        untouched = {p: p.read_bytes() for p in self.base.rglob('*')
                     if p.is_file() and p.name != 'min_freq'}
        observed = []
        self.controller.sleep = lambda seconds: observed.append((seconds, self.minimum()))
        result = self.controller.reset()
        self.assertEqual(observed, [(2.0, 625000000)])
        self.assertEqual(self.minimum(), 500000000)
        self.assertTrue(result['restored'])
        self.assertFalse(self.controller._pending().exists())
        for path, value in untouched.items():
            self.assertEqual(path.read_bytes(), value, str(path))

    def test_interrupted_wait_still_restores(self):
        def fail(_):
            raise OSError('operation interrupted')
        self.controller.sleep = fail
        with self.assertRaisesRegex(OSError, 'interrupted'):
            self.controller.reset()
        self.assertEqual(self.minimum(), 500000000)
        self.assertFalse(self.controller._pending().exists())

    def test_restore_failure_retains_journal_and_recovers_after_reload(self):
        normal_write = self.controller._write_min
        def fail_restore(value):
            if value == 500000000:
                raise OSError('temporary restore failure')
            normal_write(value)
        self.controller._write_min = fail_restore
        with self.assertRaises(OSError):
            self.controller.reset()
        self.assertEqual(self.minimum(), 625000000)
        self.assertTrue(self.controller._pending().exists())
        reloaded = self.new_controller(lambda _: None)
        self.assertTrue(reloaded.recover())
        self.assertEqual(self.minimum(), 500000000)

    def test_external_clock_change_is_not_overwritten(self):
        self.controller.sleep = lambda _: (self.gpu / 'min_freq').write_text('750000000')
        with self.assertRaisesRegex(ResetError, 'Another application'):
            self.controller.reset()
        self.assertEqual(self.minimum(), 750000000)

    def test_busy_gpu_rejected_without_any_write(self):
        (self.gpu / 'cur_freq').write_text('2230000000')
        with self.assertRaisesRegex(ResetError, 'GPU is busy'):
            self.controller.reset()
        self.assertEqual(self.minimum(), 500000000)
        self.assertFalse(self.controller._pending().exists())

    def test_locked_gpu_rejected(self):
        (self.gpu / 'max_freq').write_text('500000000')
        self.assertFalse(self.controller.status()['ready'])
        with self.assertRaisesRegex(ResetError, 'frequency is locked'):
            self.controller.reset()
        self.assertEqual(self.minimum(), 500000000)

    def test_second_process_lock_rejected(self):
        with self.controller._lock():
            with self.assertRaises(ResetError):
                self.new_controller(lambda _: None).reset()
        self.assertEqual(self.minimum(), 500000000)

    def test_old_boot_journal_does_not_change_current_limits(self):
        self.controller._save('pending.json', {'boot_id': 'old-boot',
                              'original_min': 750000000, 'pulse': 625000000})
        self.assertFalse(self.controller.recover())
        self.assertEqual(self.minimum(), 500000000)

    def test_zero_minimum_is_restored_as_zero(self):
        (self.gpu / 'min_freq').write_text('0')
        self.controller.reset()
        self.assertEqual(self.minimum(), 0)

    def test_corrupt_journal_cannot_write_an_arbitrary_frequency(self):
        self.controller._save('pending.json', {'boot_id': 'boot-one',
                              'original_min': 999999999999, 'pulse': 625000000})
        with self.assertRaises(ResetError):
            self.controller.recover()
        self.assertEqual(self.minimum(), 500000000)

    def test_status_is_read_only_and_reports_real_sensor_units(self):
        self.assertEqual(self.controller.status()['temperature_c'], 62.5)
        self.assertEqual(self.controller.status()['fan_percent'], 42)
        self.assertEqual(self.minimum(), 500000000)
        self.assertFalse(self.controller._pending().exists())

    def test_cooldown_blocks_repeated_resets(self):
        self.controller.reset()
        self.assertFalse(self.controller.status()['ready'])
        with self.assertRaisesRegex(ResetError, 'Please wait'):
            self.controller.reset()


if __name__ == '__main__':
    unittest.main()
