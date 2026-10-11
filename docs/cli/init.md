# init

```bash
para-files init [ROOT] [--apply]
```

Lists `0_Inbox` and every leaf folder from `tree.yaml` that does not exist under the PARA root yet; `--apply` creates them. ROOT defaults to `PARA_FILES_PARA_ROOT`; pass it for a new root that has no `0_Inbox` yet. A ROOT that is itself a bucket (such as `…/0_Inbox`) is refused.

Folders created by `init` are not journaled: `init` only creates empty folders the tree expects and never moves or removes anything. Remove one you did not want by hand.
