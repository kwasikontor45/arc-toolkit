# AppArmor, Fail2ban, and SOC: daily field card

Maintainer: LT-two (L2) · 2026-10-13

## Start here

- **AppArmor (AA)** puts limits around what an application can read or do. It is a seat belt for programs; it does not replace updates, account security, or backups.
- **Fail2ban (F2B)** watches selected logs and temporarily blocks repeated failures, usually login attempts. A ban is a clue to investigate, not proof that the source is malicious.

## Daily check · about two minutes

1. In **Khaos Lab → Security**, open **AppArmor: live profile status**. Or run `sudo aa-status` in a terminal. Check that expected profiles are loaded and enforced; note unexpected unconfined services or a sudden change from yesterday. Do not change a profile mode to make an alert disappear.
2. Open **Fail2ban: live status and control console**. Run `arc sec f2b` for the menu, then review status, `arc sec f2b banned`, and `arc sec f2b logs`. Confirm a ban belongs to the expected jail and is not a known admin or service before changing it.
3. Check `arc heal status`. If something changed, record the time, evidence, action, and follow-up. If a finding is unclear, preserve it and ask before disabling a control.

**Beginner rule:** observe first, verify the affected service and time window, then make one reversible change. Recheck status afterward. Do not unban an address just because it is unfamiliar, and do not ban an address without confirming the target jail and reason.

## Blue · red · purple

- **Blue team · defend:** keep protections on, review denials and bans, confirm alerts arrive, and keep a recovery path. Daily skill: tell an expected block from a service failure using time, service, and logs.
- **Red team · test:** test only your own systems or a written, named scope. Agree on the time window and safe limits first; stop if traffic reaches another target. Daily skill: write down the exact test and expected signal before running it.
- **Purple team · learn:** compare that authorized test with the logs, improve one detection or control, repeat the same bounded check, and record whether it worked. Daily skill: connect one action to one observable alert or log entry.

## Safe live controls

- **AppArmor:** the panel's reload action asks for confirmation and uses `systemctl reload apparmor`; the installed unit reloads profiles without stopping AppArmor. Review profile edits first. This station lacks the per-profile `aa-enforce` / `aa-complain` tools, so no mode toggles are exposed. Do not globally switch profiles to complain mode or unload AppArmor.
- **Fail2ban:** the terminal console opens the existing `arc sec f2b` controls. It can show status, list bans, inspect logs, test configuration, and perform a deliberate ban or unban. Verify the jail and address before changing a ban; the manual ban command targets the `sshd` jail.
- These controls need elevated access. The status console opens a real terminal so `sudo` can prompt there; the panel's profile reload uses cached, non-interactive sudo and fails closed if authorization has expired.

## Quick terminal reference

```sh
sudo aa-status
sudo systemctl reload apparmor   # only after reviewing profile changes
arc sec f2b
arc sec f2b banned
arc sec f2b logs
arc sec f2b ban <ip>             # sshd jail; verify the address first
arc sec f2b unban <ip>           # confirm it is a false positive first
```

## References

- AppArmor project documentation: <https://gitlab.com/apparmor/apparmor/-/wikis/home/>
- Fail2ban project overview and client documentation: <https://github.com/fail2ban/fail2ban>
- NIST Cybersecurity Framework 2.0: <https://www.nist.gov/cyberframework>
- OWASP Web Security Testing Guide, including authorization testing: <https://owasp.org/www-project-web-security-testing-guide/stable/2-Introduction/> and <https://owasp.github.io/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/05-Authorization_Testing/>
