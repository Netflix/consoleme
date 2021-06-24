# List

The `list` command allows you to see all of the roles you have access to via ConsoleMe. By default, only your console roles will be shown. Using the `-a` / `--all` flag will also include application roles.

```bash
weep list
Roles:
   arn:aws:iam::012345678901:role/admin
   arn:aws:iam::112345678901:role/poweruser
   arn:aws:iam::212345678901:role/readonly
   arn:aws:iam::312345678901:role/admin
...
```

