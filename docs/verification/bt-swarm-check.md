# Supplied torrent swarm verification — 2026-09-10

Scope: first selected file only; bounded duration and an 8 MiB completed-data threshold, isolated `.verification-downloads/bt-live`. No full 64.79 GiB transfer requested. Large preallocated file sizes are not received-byte evidence.

Earlier runs (90 / 180 / 60 seconds) received zero bytes; transient 3–4 peer connections did not establish usable data transfer. Additional peer diagnostics omit IP addresses and count peers with pieces, choking and interest only.

An independent UDP connect+scrape request to tracker.opentrackr.org:1337 succeeded for info hash 3af7aad38597e10936ae4bb25073302abb67b2c6. Its response reported zero seeders, zero completed downloads and zero leechers. This establishes reachability of that tracker only, not proof that no seed exists globally.

Public-only supplementary trackers were selected from https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt. Private torrents do not receive this list. IPv4 DHT bootstrap is configured. No certificate bypass, system proxy modification, or global firewall change was made.

Local web-seed engine tests are successful; they do not establish success for the supplied public torrent. Keep the remaining live-download failure explicit.
