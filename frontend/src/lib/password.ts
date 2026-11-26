export const MIN_PASSWORD_LENGTH = 12;

// No look-alike characters (0/O, 1/l/I) so a generated password can be read out or typed from a note.
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";

/** A random password from the browser's secure generator, without modulo bias. */
export function generatePassword(length = 20): string {
  const limit = 256 - (256 % ALPHABET.length); // bytes at or above this would favour early characters
  const out: string[] = [];
  while (out.length < length) {
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    for (const b of bytes) {
      if (b < limit && out.length < length) out.push(ALPHABET[b % ALPHABET.length]);
    }
  }
  return out.join("");
}
