# Episode 1163 speed regression — 2026-09-09

- Input: https://yhdm.one/vod-play/1999457734/ep1163.html
- Reproduced: the initial DOM source-link list was empty. The resolver later found the default player, but did not refresh the source links; it therefore returned hd.kuktxu.com rather than the explicitly listed IK source.
- Original complete-download attempt reproduced TLS EOF and unstable sub-MiB/s rates. Stopped the isolated baseline at about 35%; no baseline completion claim.
- Fix: refresh episode source links once the player is initialized, using the same strict source-selection function. No increased concurrency and no system proxy changes.
- Real corrected application path selected bfikuncdn.com/20260526/GVMy3prs/index.m3u8, downloaded all 484 fragments, 297.36 MiB in 17 seconds (yt-dlp average 16.92 MiB/s). Total parsing/download/verification time was 27.1 seconds.
- Returned non-skipped, actual-dimension-verified `海贼王 第1163集 1080p.mp4` in `.verification-downloads/ep1163-fixed/yhdm.one/`.
- Added delayed-source regression; 169 tests passed. Does not guarantee equivalent speed for other episodes, times, or networks.
