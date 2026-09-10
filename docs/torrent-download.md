# Local torrent download

Paste the complete local `.torrent` path into the existing input and click 智能读取. The reusable selection dialog lists file names and sizes; only selected indices are passed to aria2. Confirm adds one queue job, not an immediate download.

Torrent payloads bypass video format selection, transcoding and resolution renaming. Outputs use `BT/<torrent digest namespace>/<original torrent path>` to isolate distinct torrents. Keep the original torrent file for restart; changed metadata is rejected and must be imported again. Partial files and aria2 control data are retained for resuming. BT piece boundaries may require adjacent bytes even when only some files are selected.

Runtime: bundled aria2, process-scoped loopback RPC with random authentication, no system proxy changes. Download may upload pieces to peers while active; seed time is zero after completion. Public torrents use trackers/web seeds, IPv4 DHT and peer exchange; aria2 enforces private-torrent restrictions. Local peer discovery stays disabled. DHT state is isolated in the torrent output directory. Magnet metadata discovery is not implemented yet. Waiting progress reports connection counts, not an invented transfer rate.

Validation: supplied local torrent metadata read successfully: 20 files, about 64.79 GiB; no content transfer of that torrent started. Controlled local HTTP web-seed torrent completed with the real aria2 engine, preserving the file name and exact bytes. Regression suite includes unsafe path rejection. Public swarm availability and the supplied torrent's complete download are not verified. No installer or GitHub release produced.
