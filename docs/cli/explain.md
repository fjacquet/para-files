# explain

```bash
para-files explain FILE [--ask-model]
```

Shows the evidence read from the file, what each signal says (rules, books, issuers, model), the resulting decision, and which config entry to edit to change it. Changes nothing.

The model is asked only with `--ask-model`, since that sends the file name and the start of its text to the model (with zero data retention). For a secret file, only the reason it was flagged is shown.

```bash
para-files explain 0_Inbox/scan_0001.pdf
para-files explain 0_Inbox/scan_0001.pdf --ask-model
```
