# Embedded Media Factory

This directory contains the Google Flow Media Factory runtime bundled with
CofiDocumentary. It is intentionally source-only: mutable database, account
profiles, encrypted sessions, generated outputs and logs are stored under
`CofiDocumentary/data/media_factory`.

The embedded runtime is synchronized from the CofiStudio implementation so a
standalone CofiDocumentary copy can use AI Visual without a separate CofiStudio
installation.
