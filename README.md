# tnetstring

A pure python library implementation of the
[tnetstring](http://tnetstrings.org/) encoding.

It is heavily inspired by the [hyper](https://github.com/python-hyper)
philosophy in the sense that it's a "bring-your-own-I/O" library.
It does this by providing a `Connection` object.

The full API consists of two functions `encode()` and `decode()` and a
`Connection` object.

If you are reading/writting from/to a streaming channel (ex: socket) I advise
you to use the Connection object. This will ensure that parsing of incomplete
blocks from the stream is properly managed.

Otherwise feel free to use the simpler `encode()`/`decode()` functions.
