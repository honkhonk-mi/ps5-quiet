# Third-party components

PS5 Quiet's original code is BSD-3-Clause, as described in LICENSE. Bundled dependencies retain their own licenses:

- **@decky/api 1.1.3**, SteamDeckHomebrew Team: LGPL-2.1. See [license text](licenses/decky-api-LGPL-2.1.txt), [upstream source](https://github.com/SteamDeckHomebrew/loader-api) and the exact package version/integrity in package-lock.json. The source map also includes the API source used by the bundle.
- **react-icons 5.7.0**, Copyright 2018 kamijin_fanta: MIT. See [license and icon collection notices](licenses/react-icons.txt) and [upstream source](https://github.com/react-icons/react-icons).
- The **fan** icon (`FaFan`) is from **Font Awesome Free 5**, by Fonticons, Inc., under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). [Font Awesome](https://fontawesome.com/) · [original icons and license](https://github.com/FortAwesome/Font-Awesome/tree/5.x). The icon artwork is unchanged; react-icons provides its React representation.

React and @decky/ui are supplied by Decky at runtime and are not bundled in index.js. The lockfile records the build dependencies.

To inspect or modify a bundled component, clone the corresponding release tag, run `npm ci --ignore-scripts`, modify the dependency or application source, and rebuild using the commands in README.md. The plugin does not restrict rebuilding, replacement or debugging of these components.
