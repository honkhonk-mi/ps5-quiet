# PS5 Quiet

A Decky Loader button for a PS5 Linux hot-idle workaround: briefly reapply the GPU minimum frequency, then restore it. Use it from the Steam menu **with the game closed** when the console stays unusually hot at idle.

[Русская инструкция](README.ru.md) · [Download](https://github.com/honkhonk-mi/ps5-quiet/releases/latest) · [Report a problem](https://github.com/honkhonk-mi/ps5-quiet/issues)

## What it does

Press **Decky → PS5 Quiet → «Утихомирить фаны»** (“Quiet the fans”). The current interface is in Russian; it displays temperature and the fan PWM percentage, not RPM.

The plugin raises the minimum GPU clock by one supported step for two seconds, then restores the original minimum. On the tested system that is **500 → 625 → 500 MHz**. The next step is selected from the driver's available frequencies and cannot exceed the current maximum. A locked frequency range or reported GPU load blocks the operation.

It does not write fan controls, CoolerControl profiles, the GPU governor, maximum GPU frequency, or CPU settings. CoolerControl continues controlling the fan. Do not change GPU clock settings in another application during the two-second operation.

This is an experimental workaround for an observed driver state, not a universal overheating fix. A successful button press means the frequency operation completed; it does not guarantee cooling. Driver-reported clocks are not an independent hardware clock measurement, and the underlying cause is not established.

## Compatibility and observed result

Tested on one original PS5 running **PS5 Bazzite Deck v2.7.3, kernel 7.3.1-viva and Decky Loader v3.3.1**, with CoolerControl active. In one idle check the temperature fell from **63.5 °C to approximately 49–52 °C** over the following 30 seconds, and fan PWM fell from **43% to 24–25%**. The original minimum and maximum GPU settings were preserved. Other models and kernels have not been verified.

Requires the PS5 kernel interface at `/sys/class/devfreq/ps5-gpufreq` and Decky Loader with API 1 support. This is not for stock PS5 firmware or ordinary Steam Deck hardware. Missing interfaces are reported as unsupported.

## Install

1. Install [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) on your existing PS5 Linux setup.
2. Open [Releases](https://github.com/honkhonk-mi/ps5-quiet/releases/latest) and download **`ps5-quiet-v1.0.1.zip`** from Assets. GitHub's automatic “Source code” archives are for development, not installation.
3. In Decky settings, enable Developer Mode if needed. Under **Developer**, choose **Install Plugin from ZIP File**, select the downloaded ZIP and accept Decky's third-party plugin prompt. The plugin requires root access to write the GPU frequency interface.
4. Close the game, open **Decky → PS5 Quiet**, press **«Утихомирить фаны»**, and allow a short time for the temperature and fan response. Repeated presses have a ten-second cooldown.

You can also paste the release asset's direct download link into Decky's **Install Plugin from URL** field.

To uninstall, wait for any operation to finish and remove **PS5 Quiet** in Decky's plugin settings. There is no separate service or automatic reset on login to remove.

## Interrupted operations

Before changing the minimum, the plugin saves a small recovery record in its Decky runtime directory. A normal startup only reads hardware. If an operation was interrupted during the same Linux boot, startup attempts to restore its own temporary minimum. Records from earlier boots are discarded without applying their clock settings. If another tool changed the minimum, its value is preserved and the plugin reports a conflict. This is best-effort recovery; the driver must still accept writes.

## Build and test

Use Node.js 24, npm and Python 3.10 or newer on Linux or macOS:

```sh
npm ci --ignore-scripts
npm run typecheck
npm test
npm run build
python3 scripts/package.py
```

The install ZIP and SHA-256 checksum are written to `artifacts/`. Packaging uses a fixed allowlist and includes neither dependencies nor local runtime records.

The tests use simulated sysfs files. They cover restoration after errors, interrupted-operation recovery, external clock changes, lock contention, busy and fixed-clock rejection, cooldowns, boot boundaries and read-only fan access. They do not prove thermal behavior on every console. The live check exercised the plugin through Decky's backend API; automated tests do not exercise Steam's visual interface.

When reporting an issue, include the PS5 model, distro/kernel and Decky versions, whether a game was open, the plugin's message and before/after temperatures. Remove credentials and private identifiers from logs.

## License and credits

BSD-3-Clause. Based on the official [Decky plugin template](https://github.com/SteamDeckHomebrew/decky-plugin-template), using `@decky/api` and `@decky/ui`. See [LICENSE](LICENSE).

[Third-party licenses](THIRD_PARTY.md).
