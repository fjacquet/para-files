# init

```bash
para-files init [ROOT] [--apply]
```

Lists `0_Inbox` and every leaf folder from `tree.yaml` that does not exist under the PARA root yet; `--apply` creates them. ROOT defaults to `PARA_FILES_PARA_ROOT`; pass it for a new root that has no `0_Inbox` yet. A ROOT that is itself a bucket (such as `…/0_Inbox`) is refused.

`init --apply` is journaled like any other run: `para-files undo` removes the folders it created (only while they are still empty).
