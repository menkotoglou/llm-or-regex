# Word lists

`en.txt` is the English list from
[List of Dirty, Naughty, Obscene, and Otherwise Bad Words](https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words)
(LDNOOBW), © 2012–2020 Shutterstock, Inc., licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It is included unmodified, exactly as
`scripts/fetch_wordlist.sh` downloads it, and is the `regex` arm: a case-insensitive,
word-boundary match against every entry.

It is here as the naive baseline, not as a recommendation. The talk's point is that a short,
curated list is a good *guardrail* around a model, and a poor model on its own.
