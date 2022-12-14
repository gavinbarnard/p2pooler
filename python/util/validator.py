#!/usr/bin/env python
# * p2pooler
# * Copyright 2022      grb         <https://github.com/gavinbarnard>
# *
# *   This program is free software: you can redistribute it and/or modify
# *   it under the terms of the GNU General Public License as published by
# *   the Free Software Foundation, either version 3 of the License, or
# *   (at your option) any later version.
# *
# *   This program is distributed in the hope that it will be useful,
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *   GNU General Public License for more details.
# *
# *   You should have received a copy of the GNU General Public License
# *   along with this program. If not, see <http://www.gnu.org/licenses/>.
# */

from monero.address import address, IntegratedAddress, SubAddress, Address

def is_integrated(test_address):
    a = address(test_address)
    if type(a) == IntegratedAddress:
        return True
    return False

def validate_address(test_address):
    try:
        a = address(test_address)
    except Exception:
        return False
    return True

if __name__ == "__main__":
    print("running test")
    assert validate_address("41jyth3Xv8vJPTRBPNXfLJ29jo2do8aC2CPXXeCNHCFRjjNhZ1GB2HETntXWAJqgr2Y9my5XTanKKWFzRZG8scX13AUNYWq") == True
    assert validate_address("donkey_balls") == False
    assert validate_address(None) == False
    assert is_integrated("4GdoN7NCTi8a5gZug7PrwZNKjvHFmKeV11L6pNJPgj5QNEHsN6eeX3DaAQFwZ1ufD4LYCZKArktt113W7QjWvQ7CW86FNFap1nBMHne6V2") == True
    assert is_integrated("41jyth3Xv8vJPTRBPNXfLJ29jo2do8aC2CPXXeCNHCFRjjNhZ1GB2HETntXWAJqgr2Y9my5XTanKKWFzRZG8scX13AUNYWq") == False
    print("finish tests without assertion")