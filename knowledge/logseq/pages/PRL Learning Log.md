title:: PRL Learning Log

- Topic::
- My explanation::
- Worked example::
- Experiment / test::
- What I still do not understand::
- Links to code / evidence::

- PRL-003 concept:: A frame index plus reported FPS is a nominal playback
  position, not an exposure timestamp. Equal three-view stream structure is
  useful for visualization but cannot establish physical synchronization.

- PRL-004 concept:: A manifest records what was *observed* (relative path, size,
  SHA-256, decoder metadata) so data can stay in place. A matching hash proves
  the bytes are unchanged, not that the recording is correct or synchronized.
  Resolver code is an adapter at the filesystem boundary; the manifest records
  in `domain/` stay free of I/O.
