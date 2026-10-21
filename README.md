# prism-console-ryan-vo — Ryan Vo | AI & Machine Learning

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


> First working checkpoint. All backend and frontend tests pass. See PLAN.md for the roadmap.


Prism Console helps a developer check a generated command-line interface before spending time repairing it by hand. Agents often emit a short lifecycle vocabulary (`start`, `stop`, `status`, `chat`, `meeting`) that does not match the handlers an application already exposes, and those commands still fail when they are run. This checkpoint scores a source-grounded catalog against that thin baseline. The intended user is a developer reviewing commands for an application whose callable surfaces can be declared, or pasted as a narrow Python or `ipcMain.handle` subset.

Maintainer: Ryan Vo <ryandtvo@gmail.com>
