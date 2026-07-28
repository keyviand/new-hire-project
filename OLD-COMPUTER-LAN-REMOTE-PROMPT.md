# Prompt for Codex on my old computer

You are running on my old Windows computer. Set up this computer as my second
private LAN Remote host so I can switch between it and my main computer from my
phone.

Known machines:

- This old computer: `DESKTOP-VE6Q0ES`
- This old computer's Tailscale DNS name:
  `desktop-ve6q0es.tail55939a.ts.net`
- Main computer LAN Remote:
  `https://key.tail55939a.ts.net/`
- Expected old-computer LAN Remote:
  `https://desktop-ve6q0es.tail55939a.ts.net/`

You are authorized to install the supplied LAN Remote files, required Python
packages, the LAN Remote Windows service, and Tailscale Serve on this computer.
Do not delete or alter unrelated files, applications, network settings, or
existing Tailscale configuration.

Use this procedure:

1. Confirm that `hostname` is `DESKTOP-VE6Q0ES`, that Tailscale is connected,
   and that the main computer is reachable. Stop and report the mismatch if
   this prompt is running on another machine.
2. Locate `LAN-Remote-Old-PC-Setup-v2.zip`. Use the `v2` archive and ignore the
   older archive without `v2` in its filename. Check Downloads, Desktop, and
   the Tailscale file inbox. If it is still queued, retrieve it with
   `tailscale file get` into a new folder under Downloads.
3. Use `C:\Users\keyvi\LAN Remote Old Host` as the installed application
   directory, outside OneDrive. If that directory does not exist, extract the
   package there. If LAN Remote is already installed there, extract the new ZIP
   to a temporary staging directory and update only the supplied source and
   setup files. Preserve the existing `auth.json`, `secure-input.key`, recovery
   information, and logs. Do not run the host from the shared OneDrive project
   folder.
4. Confirm that the package contains no `auth.json`, `secure-input.key`, log
   files, recovery codes, passwords, or authenticator secrets. Never copy
   those files from the main computer. This old computer must generate its own
   authentication configuration and secure-input key.
5. Inspect the supplied scripts before running them. Install the Python
   requirements. If the required .NET SDK is missing, install the compatible
   .NET 10 SDK before building the Windows service.
6. Run `install_service.ps1`. It should request administrator approval, stop
   only the existing LAN Remote agent, build and install `LanRemoteService`,
   set it to Automatic, start it as LocalSystem, and start the unprivileged web
   agent. Tell me clearly when I need to click **Yes** on a Windows
   administrator prompt; do not try to bypass or automate UAC.
7. Verify that the service is Running/Automatic and that these listeners exist:

   - `127.0.0.1:8765` — authenticated viewer, proxied by Tailscale Serve;
   - `127.0.0.1:8766` — authenticated secure-input service relay;
   - `127.0.0.1:8767` — localhost-only host administration.

   Confirm `http://127.0.0.1:8767/host` opens on this old computer. Port 8767
   must never be added to Tailscale Serve or exposed through a firewall rule.
8. Inspect `tailscale serve status` before changing it. Preserve any unrelated
   existing Serve configuration. If there is no conflict, configure private,
   tailnet-only HTTPS forwarding with:

   `tailscale serve --bg --yes http://127.0.0.1:8765`

   Do not enable Funnel, public port forwarding, or a public firewall rule.
9. Open `http://127.0.0.1:8767/host` for me. If authentication is already
   configured, preserve it and do not reset it. If setup is still required,
   pause so I can personally create a new 12+ character password, enroll this
   host as a separate authenticator entry, enter the current 2FA code, and save
   the new recovery codes. Do not read, log, copy, or reuse my password, OTP,
   TOTP secret, or recovery codes.
10. After I confirm security setup is complete, help me enable unattended
    control from the localhost-only host panel so a successful password + 2FA
    login can control this old computer.
11. Verify from the old computer and, where possible, from the tailnet that
    `https://desktop-ve6q0es.tail55939a.ts.net/` returns the LAN Remote viewer.
    From a logged-out tailnet request, confirm `/status` returns HTTP 401 and
    `/host` returns HTTP 403. Confirm the authenticated viewer has:

    - the **Computer** selector with **Main computer** and **Old computer**;
    - full-screen mode;
    - the collapsible computer-key tray;
    - Ctrl, Alt, Shift, Windows, arrows, editing/navigation keys, and F1-F12;
    - the confirmed and rate-limited Ctrl+Alt+Delete service path;
    - the hideable phone keyboard and zoom controls.

12. Do not trigger a real Ctrl+Alt+Delete during unattended testing because it
    would interrupt the desktop. Verify its code, service build, Windows policy,
    and local authenticated relay instead.
13. Test responsive layout at a phone-sized viewport and a desktop viewport,
    check browser errors, verify that the LAN Remote service survives a web
    process restart, and confirm Tailscale Serve remains tailnet-only.
14. Finish by reporting:

    - the exact old-computer viewer URL;
    - LAN Remote service status and startup type;
    - Tailscale Serve status;
    - whether unattended control is enabled;
    - whether both computer-switcher destinations are present;
    - whether remote `/host` is blocked while local port 8767 works;
    - any remaining step that requires me.

Keep the two computers' authentication and service keys independent. Switching
computers should only navigate between the two allowlisted Tailscale HTTPS
addresses; it must never transmit credentials from one host to the other.
