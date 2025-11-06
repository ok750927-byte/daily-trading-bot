# Team notice: imminent force-push to rewrite history

We will perform a destructive history rewrite to remove sensitive file(s) (`secrets.json`) from the repository history and replace the remote history with the rewritten local history.

This is a disruptive operation. Please READ CAREFULLY and follow the instructions.

What we're changing:
- Remove `secrets.json` from all commits in the repository history.

Immediate actions required from all developers BEFORE the force-push:
1. Rotate/replace any exposed credentials (recommended). This must be done on provider side (broker API, Discord webhook, etc.). Use `docs/KEY_ROTATION_TEMPLATES.md` and `docs/SECRET_ROTATION.md`.
2. Backup any local work; create local clones if necessary. The force-push will change commit hashes.

After we perform the force-push (what you must do locally):
1. Move any uncommitted local work aside (stash or copy folder).
2. Delete your local repository clone and re-clone from remote, OR reset your local branches as follows:

   # Option A: re-clone (recommended)
   git clone <repo-url>

   # Option B: if you must preserve local branches (advanced)
   git fetch --all
   git reset --hard origin/<branch>

2. Recreate any local branches or cherry-pick work from your backups.

Timeline & contact
- Planned time: TBD (coordinate with team)
- Contact: @team-lead (please replace with actual contact)

If you have questions or are not ready, reply to this message BEFORE the force-push.
