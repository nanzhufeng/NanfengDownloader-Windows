# Episode 1149 real download verification — 2026-09-09

- Input: https://yhdm.one/vod-play/1999457734/ep1149.html
- Original visible JY source: hd.kuktxu.com/play/1aKKqPza/index.m3u8. Reproduced TLS EOF on the inherited network route. Direct requests returned valid manifest and fragments, but a full direct run stalled and was stopped; it is not counted as success.
- The same episode page explicitly lists IK: https://bfikuncdn.com/20251109/8l5KHJ4q/index.m3u8. No episode URL or media URL was guessed.
- Added site-scoped selection of that explicit episode source; unrelated pages retain normal player discovery. This does not claim every source or every episode is verified.
- Added one task-local direct attempt for unexpected TLS EOF when there is no explicit proxy override. System proxy and certificate verification are unchanged. Missing fragments now fail instead of being skipped into empty/incomplete output.
- Real production `download_with_quality_choice` path, automatic original quality: all 720 fragments downloaded in 53 seconds, 313.62 MiB transferred, average 5.86 MiB/s. Returned a non-skipped final file named `海贼王 第1149集 1080p.mp4` under `.verification-downloads/ep1149-fixed/yhdm.one/`.
- Separate complete IK download: ffprobe reports 1920x1080, audio stream, duration 1451.237 seconds, 317833545 bytes. Full ffmpeg decode exited 0; source timestamp warnings were emitted. No interactive player acceptance performed.
- Regression suite: 168 tests passed. No installer or GitHub release created.
