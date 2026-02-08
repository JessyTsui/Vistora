# Telegram Ops Design

## Product loop

1. User joins official Telegram channel.
2. User interacts with bot (`/balance`, `/topup`, `/create`).
3. Bot submits job to Vistora API.
4. Job consumes credits and returns completion callback.
5. User receives output link or retrieval instructions.

## Credit model

- Unit: credits
- Pricing suggestion:
  - base credits by duration/resolution
  - surcharge by premium quality mode
- Refund policy:
  - full refund on failed jobs
  - partial refund on canceled queued jobs

## API mapping

- Topup: `POST /api/v1/credits/{user_id}/topup`
- Query: `GET /api/v1/credits/{user_id}`
- Create job: `POST /api/v1/jobs`
- Job poll: `GET /api/v1/jobs/{id}`

## Bot command examples

- `/balance`
- `/topup 100`
- `/restore <file_id> quality=high`
- `/order <job_id>`

## Security checklist

- validate Telegram signatures/webhook source
- per-user rate limiting
- anti-abuse checks for uploads
- keep audit logs for topup and consumption
