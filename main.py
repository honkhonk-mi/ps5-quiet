import asyncio
import decky
from gpu_reset import GPUReset


class Plugin:
    def __init__(self):
        self.controller = None
        self.operation = None
        self.startup_error = None

    async def _main(self):
        self.controller = GPUReset(decky.DECKY_PLUGIN_RUNTIME_DIR)
        try:
            if await asyncio.to_thread(self.controller.recover):
                decky.logger.info('Restored minimum after interrupted reset')
        except Exception as error:
            self.startup_error = str(error)
            decky.logger.exception('Could not recover GPU reset')

    async def get_status(self):
        if self.controller is None:
            return {'supported': False, 'ready': False, 'reason': 'Плагин запускается…'}
        result = await asyncio.to_thread(self.controller.status)
        if self.startup_error:
            result.update(ready=False, reason=self.startup_error)
        return result

    async def quiet_gpu(self):
        if self.controller is None:
            return {'ok': False, 'error': 'Плагин ещё запускается.'}
        if self.operation is not None and not self.operation.done():
            return {'ok': False, 'error': 'Сброс уже выполняется.'}
        self.operation = asyncio.create_task(asyncio.to_thread(self.controller.reset))
        try:
            result = await asyncio.shield(self.operation)
            self.startup_error = None
            decky.logger.info('GPU minimum: %s -> %s -> %s Hz',
                              result['original_min'], result['pulse'], result['original_min'])
            return {'ok': True, 'result': result}
        except Exception as error:
            decky.logger.exception('GPU reapply failed')
            return {'ok': False, 'error': str(error)}

    async def _unload(self):
        if self.operation is not None and not self.operation.done():
            try:
                await asyncio.shield(self.operation)
            except Exception:
                decky.logger.exception('Error finishing GPU reset during unload')

    async def _uninstall(self):
        await self._unload()
