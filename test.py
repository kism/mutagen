import struct
import zlib

class OggCRC:
    """OGG CRC calculation"""
    def __init__(self):
        self.crc_table = self._build_crc_table()

    def _build_crc_table(self):
        table = []
        for i in range(256):
            crc = i
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0x04C11DB7
                else:
                    crc >>= 1
            table.append(crc & 0xFFFFFFFF)
        return table

    def calculate(self, data):
        crc = 0
        for byte in data:
            crc = self.crc_table[(crc ^ byte) & 0xFF] ^ (crc >> 8)
        return crc ^ 0xFFFFFFFF

def create_valid_vorbis_header():
    """Create a minimal but valid Vorbis identification header"""
    # Vorbis packet type 1 (identification)
    packet_type = 1
    vorbis_string = b"vorbis"

    # Vorbis identification header fields
    version = 0
    channels = 2
    sample_rate = 44100
    bitrate_max = 0
    bitrate_nominal = 128000
    bitrate_min = 0
    blocksize_0 = 8  # 2^8 = 256
    blocksize_1 = 11  # 2^11 = 2048
    framing_flag = 1

    # Pack the header properly
    header = struct.pack("<B", packet_type)  # packet type
    header += vorbis_string  # "vorbis"
    header += struct.pack("<I", version)  # version
    header += struct.pack("<B", channels)  # channels
    header += struct.pack("<I", sample_rate)  # sample rate
    header += struct.pack("<I", bitrate_max)  # bitrate maximum
    header += struct.pack("<I", bitrate_nominal)  # bitrate nominal
    header += struct.pack("<I", bitrate_min)  # bitrate minimum
    header += struct.pack("<B", (blocksize_1 << 4) | blocksize_0)  # blocksizes
    header += struct.pack("<B", framing_flag)  # framing flag

    return header

def create_ogg_page(data, serial_number, page_sequence, granule_pos=0, header_type=0, invalid_segments=False):
    """Create an OGG page with optional invalid segment count"""

    # Split data into segments (max 255 bytes per segment)
    segments = []
    pos = 0
    while pos < len(data):
        segment_size = min(255, len(data) - pos)
        segments.append(data[pos:pos + segment_size])
        pos += segment_size

    # Create segment table
    segment_table = bytes([len(seg) for seg in segments])

    # This is where we make it invalid
    if invalid_segments:
        # Claim more segments than we actually have
        reported_segments = len(segments) + 200  # Claim 10 more segments
        # But keep the same segment table (this creates the mismatch)
    else:
        reported_segments = len(segments)

    # Build page header
    capture_pattern = b"OggS"
    version = 0

    header_without_crc = struct.pack(
        "<4sBBQIIIB",
        capture_pattern,
        version,
        header_type,
        granule_pos,
        serial_number,
        page_sequence,
        0,  # CRC placeholder
        reported_segments  # This is the invalid part
    )

    # Combine all page data
    page_data = header_without_crc + segment_table + b"".join(segments)

    # Calculate CRC with the CRC field set to 0
    crc_calc = OggCRC()
    crc = crc_calc.calculate(page_data)

    # Rebuild header with correct CRC
    header_with_crc = struct.pack(
        "<4sBBQIIIB",
        capture_pattern,
        version,
        header_type,
        granule_pos,
        serial_number,
        page_sequence,
        crc,
        reported_segments
    )

    return header_with_crc + segment_table + b"".join(segments)

def create_convincing_invalid_ogg():
    """Create a more convincing OGG file that starts valid but becomes invalid"""

    serial_number = 0
    pages = []

    # Page 0: Valid Vorbis identification header
    vorbis_header = create_valid_vorbis_header()
    page0 = create_ogg_page(vorbis_header, serial_number, 0, 0, 0x02)  # BOS flag
    pages.append(page0)

    # Page 1: Valid comment header (minimal)
    comment_header = struct.pack("<B", 3) + b"vorbis" + struct.pack("<I", 0) + struct.pack("<I", 0) + struct.pack("<B", 1)
    page1 = create_ogg_page(comment_header, serial_number, 1, 0, 0)
    pages.append(page1)

    # # Page 2: Valid setup header (minimal)
    # setup_header = struct.pack("<B", 5) + b"vorbis" + b"\x00" * 10 + struct.pack("<B", 1)
    # page2 = create_ogg_page(setup_header, serial_number, 2, 0, 0)
    # pages.append(page2)

    # # Page 3: THIS is where we make it invalid - audio data with wrong segment count
    # audio_data = b"AUDIO" * 100  # Some fake audio data
    # page3 = create_ogg_page(audio_data, serial_number, 3, 4410, 0, invalid_segments=True)
    # pages.append(page3)

    return b"".join(pages)

def write_convincing_invalid_ogg(filename):
    data = create_convincing_invalid_ogg()
    with open(filename, 'wb') as f:
        f.write(data)
        f.write(b"\x00" * 2) # lil extra for fun
    print(f"Created convincing invalid OGG file: {filename}")
    print("- Has valid Vorbis headers in first 3 pages")
    print("- Page 3 has invalid segment count (claims more segments than present)")

if __name__ == "__main__":
    write_convincing_invalid_ogg("convincing_invalid.ogg")





import mutagen

audio = mutagen.File("convincing_invalid.ogg")
# audio = mutagen.File("test.ogg")

audio['artist'] = "Brad Sucks"

audio.save()
