# Security

## Public repository rules

- Never commit database backups or data files (`.bak`, `.backup`, `.mdf`, `.ldf`).
- Never commit `.env` files, passwords, API keys, tokens, private keys, or personal records.
- Keep generated save files, AI checkpoints, public tunnel URLs, and gameplay traces ignored.
- Use example configuration files with placeholders for anything other developers must configure.
- Treat any secret or personal data committed to Git as exposed, even after deleting the latest copy, because older commits remain downloadable.

## Network safety

Local servers bind to `127.0.0.1` by default. Scripts that bind to `0.0.0.0`
are for trusted LAN testing only and display a confirmation warning. Do not
forward their ports to the internet. The temporary public-game launcher binds
the game to loopback and exposes only the browser game through its temporary
Cloudflare tunnel.

## Reporting a vulnerability

Do not publish credentials, personal information, or exploit details in a
public issue. Contact the repository owner privately and rotate any exposed
credential immediately.
