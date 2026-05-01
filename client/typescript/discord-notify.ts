/**
 * discord-notify TypeScript client
 * Copy this file directly into your project — no npm package needed.
 *
 * Two usage patterns:
 *
 * 1. Module-level (quick one-off):
 *    import { notify } from './discord-notify'
 *    await notify.success('1485916068307533937', 'Sync complete')
 *
 * 2. Configured instance (recommended):
 *    import { DiscordNotifier } from './discord-notify'
 *    const notifier = new DiscordNotifier(process.env.DISCORD_NOTIFY_CHANNEL!)
 *    await notifier.success('Sync complete', { body: '42 events' })
 *    await notifier.error('Sync failed', { channel_id: process.env.DISCORD_ERROR_CHANNEL })
 */
import http from 'http'

const SOCKET_PATH = process.env.DISCORD_NOTIFY_SOCKET ?? '/tmp/discord-notify.sock'

type Level = 'info' | 'success' | 'error' | 'warn'

interface SendOptions {
  body?: string
  fields?: Record<string, string>
  file_path?: string
  project?: string
}

interface InstanceOptions extends SendOptions {
  channel_id?: string  // override default
}

function send(channel_id: string, level: Level, title: string, options: SendOptions = {}): Promise<void> {
  const payload = JSON.stringify({
    channel_id,
    level,
    title,
    ...(options.body && { body: options.body }),
    ...(options.fields && { fields: options.fields }),
    ...(options.file_path && { file_path: options.file_path }),
    ...(options.project && { project: options.project }),
  })

  return new Promise((resolve) => {
    const req = http.request(
      {
        socketPath: SOCKET_PATH,
        path: '/notify',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload),
        },
      },
      (res) => { res.resume(); resolve() },
    )
    req.on('error', (e) => { console.error(`[discord-notify] failed: ${e.message}`); resolve() })
    req.write(payload)
    req.end()
  })
}

export class DiscordNotifier {
  constructor(private defaultChannelId: string, private project?: string) {}

  private resolve(options: InstanceOptions): [string, SendOptions] {
    const { channel_id, ...rest } = options
    return [channel_id ?? this.defaultChannelId, { ...rest, project: rest.project ?? this.project }]
  }

  success(title: string, options: InstanceOptions = {}) {
    const [ch, opts] = this.resolve(options)
    return send(ch, 'success', title, opts)
  }
  error(title: string, options: InstanceOptions = {}) {
    const [ch, opts] = this.resolve(options)
    return send(ch, 'error', title, opts)
  }
  info(title: string, options: InstanceOptions = {}) {
    const [ch, opts] = this.resolve(options)
    return send(ch, 'info', title, opts)
  }
  warn(title: string, options: InstanceOptions = {}) {
    const [ch, opts] = this.resolve(options)
    return send(ch, 'warn', title, opts)
  }
}

// Module-level convenience (must pass channel_id explicitly)
export const notify = {
  success: (channel_id: string, title: string, options?: SendOptions) => send(channel_id, 'success', title, options),
  error:   (channel_id: string, title: string, options?: SendOptions) => send(channel_id, 'error',   title, options),
  info:    (channel_id: string, title: string, options?: SendOptions) => send(channel_id, 'info',    title, options),
  warn:    (channel_id: string, title: string, options?: SendOptions) => send(channel_id, 'warn',    title, options),
}
