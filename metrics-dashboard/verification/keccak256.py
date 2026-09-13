#!/usr/bin/env python3
"""Pure-Python Keccak-256 (FIPS 202 aligned with Ethereum's keccak256).

Used only for offline ABI conformance checks in DPA-182 -- the on-chain path is
Node/ethers (contracts/). Keccak preimages are NOT an attack target here; we
only need an independent implementation to cross-check ethers' function
selectors against contracts/AuditTrail.abi.json.
"""

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]

_ROT = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 45, 2],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14],
]


def _rotl(x, n):
    return ((x << n) | (x >> (64 - n))) & 0xFFFFFFFFFFFFFFFF


def _keccak_f(state):
    for rc in _RC:
        # theta
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rotl(c[(x + 1) % 5], 1) for x in range(5)]
        for y in range(5):
            for x in range(5):
                state[x + 5 * y] ^= d[x]
        # rho + pi
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rotl(state[x + 5 * y], _ROT[x][y])
        # chi
        for y in range(5):
            for x in range(5):
                state[x + 5 * y] = b[x + 5 * y] ^ ((~b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y])
        # iota
        state[0] ^= rc
    return state


def keccak256(data: bytes) -> bytes:
    rate = 136  # 1088 bits for keccak-256
    state = [0] * 25

    padded = bytearray(data)
    padded.append(0x01)  # keccak padding (not sha3's 0x06)
    while len(padded) % rate != 0:
        padded.append(0x00)
    padded[-1] |= 0x80

    for off in range(0, len(padded), rate):
        block = padded[off:off + rate]
        for i in range(rate // 8):
            lane = int.from_bytes(block[i * 8:(i + 1) * 8], "little")
            state[i] ^= lane
        _keccak_f(state)

    out = b"".join(state[i].to_bytes(8, "little") for i in range(4))
    return out


def selector(sig: str) -> str:
    return "0x" + keccak256(sig.encode("utf-8"))[:4].hex()


if __name__ == "__main__":
    import sys
    for sig in sys.argv[1:]:
        print(f"{sig} -> {selector(sig)}")