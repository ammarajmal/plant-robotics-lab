# Deterministic video ingestion

PRL video ingestion is deliberately smaller than a tracking system. It reads
media, records decoder-reported metadata, and pairs frames by nominal index. It
does not identify plants, track targets, render displays, or control hardware.

## Contracts

- `VideoStreamInfo` describes width, height, reported FPS, and reported frame count.
- `FrameTiming` stores a zero-based frame index, `frame_index / fps`, and the
  explicit `nominal_frame_index` provenance label.
- `FramePacket` combines one decoded array with its stream and timing metadata.
- `ViewSpec` names one input path.
- `ThreeViewPacket` contains the ordered `left_arm`, `middle`, and `right_arm`
  packets and always reports `nominal_frame_index_only` synchronization status.

## Why a frame is not a camera timestamp

A video frame is a decoded representation of compressed pixels. The container's
FPS and frame index provide a playback position, not the instant when the
camera sensor exposed the scene. Equal frame numbers can therefore be useful
for visualization while remaining insufficient for motion-accurate fusion.

## Resource safety and failure behavior

Each `VideoCapture` is opened inside a bounded operation and released in a
`finally` block. The three-view generator also releases all captures if the
consumer stops early. Missing files, corrupt streams, invalid metadata, and
decode failures raise explicit exceptions. Unequal stream lengths, dimensions,
or reported FPS values fail before yielding a packet; PRL does not silently
truncate, duplicate, substitute, or skip frames.

## Why decoding is separate from tracking

Decoding answers “what pixels were present at this playback index?” Tracking
answers “which pixels belong to the same physical target over time?” Keeping
these layers separate makes codec failures testable without detector behavior,
allows multiple trackers to consume the same packets, and prevents a tracking
heuristic from hiding missing or invalid media.

Synthetic videos are used for automated tests because they are local,
repeatable, cheap, and controllable. The MP4 `mp4v` codec is lossy in this
environment, so tests assert shape, dtype, repeatability, and tolerant pixel
statistics rather than exact encoded fill values.

## What three equal streams do and do not show

Equal FPS, dimensions, and frame counts show structural compatibility for a
nominal playback iterator. They do not show shared camera clocks, exposure
times, dropped-frame absence, cross-view target identity, calibration, or valid
3D correspondence. Those require separate evidence and contracts.
