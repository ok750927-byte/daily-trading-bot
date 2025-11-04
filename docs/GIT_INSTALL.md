Git installation and verification (Windows)
=========================================

This project uses git for version control. If `git` is not available on your
Windows environment, follow one of the methods below to install it and make
it available from `cmd.exe`.

1) Quick verification

   Open `cmd.exe` and run:

   ```cmd
   where git
   git --version
   ```

   If these return a path and a version string (e.g. `git version 2.4x.x`),
   you're good to go.

2) Recommended: winget (Windows 10/11)

   ```cmd
   winget install --id Git.Git -e --source winget
   git --version
   ```

3) GUI installer (manual)

   - Download from: https://git-scm.com/download/win
   - Run the installer. When asked about PATH, choose:
     "Git from the command line and also from 3rd-party software"
   - Finish install and open a new cmd:

   ```cmd
   git --version
   ```

4) Chocolatey (if available)

   ```powershell
   choco install git -y
   git --version
   ```

5) If `git` is installed but `cmd.exe` cannot find it

   - Typical install paths: `C:\Program Files\Git\cmd` or `C:\Program Files\Git\bin`
   - Add the folder containing `git.exe` to your PATH environment variable
     (Control Panel → System → Advanced system settings → Environment Variables → Path → Edit).

After installation, re-run the quick verification commands to confirm git is available.
