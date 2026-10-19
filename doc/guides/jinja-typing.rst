.. _jinja typing:

Jinja template typing
=====================

Pycroft type-checks Jinja templates with
`types-for-jinja <https://github.com/agdsn/types-for-jinja>`_
and the same type checker run used for Python.

Templates declare their context in a ``{#def … #}`` comment.
``types-for-jinja generate`` writes line-aligned stubs under ``_jinja_stubs/``
(gitignored). The type checker checks those stubs; ``types-for-jinja remap`` rewrites
diagnostics back to template paths.

CLI
---

Prerequisites
    * a venv from ``uv sync`` / ``just local-setup``

One-shot check of templates only::

    just check-jinja

Re-run that check when files under ``web/templates`` change
(uses ``watchdog`` via ``uv``, no system ``inotifywait``)::

    just watch-jinja

CI runs the same generation step before the full project ``mypy``
(see ``scripts/run_mypy.sh``).

Layers
------

=============== =============================================================== =========================================
Layer           Role                                                            How to get it
=============== =============================================================== =========================================
CI / CLI        Fail the build on bad template types                            automatic in CI; ``just check-jinja``
LSP             Live stub regen + completion/hover in the template buffer       ``types-for-jinja-lsp`` (``types-for-jinja[lsp]``)
Diagnostic mirror Show checker errors *on* the ``.html`` buffer                 Neovim (upstream); not Helix/PyCharm yet
=============== =============================================================== =========================================

Editor setup
------------

The LSP itself does **not** put mypy/ty/pyright errors on the template
buffer. A thin editor-side *diagnostic mirror* republishes stub diagnostics
onto the ``.html``; Neovim has one (see
`types-for-jinja — In your editor <https://github.com/agdsn/types-for-jinja/tree/main/docs#in-your-editor>`_),
Helix and PyCharm do not yet. Without a mirror, type errors still come from
``just check-jinja`` / ``just watch-jinja`` (or CI). What the LSP *does*
give you in the ``.html`` is completion, hover, and regenerating
``_jinja_stubs`` as you edit — useful while authoring ``{#def #}`` contexts
and attribute access, not as a substitute for the checker.

Helix
~~~~~

After ``uv sync``, put something like the following in
``.helix/languages.toml`` (local to your checkout; not committed).
Point ``command`` at ``.venv/bin/types-for-jinja-lsp`` if the binary is
not on ``PATH``::

    [language-server.types-for-jinja]
    command = "types-for-jinja-lsp"

    [[language]]
    name = "jinja"
    file-types = [
      "jinja", "jinja2", "j2",
      { glob = "web/templates/**/*.html" },
    ]
    language-servers = ["types-for-jinja"]

PyCharm
~~~~~~~

PyCharm supports Jinja natively. To also get the LSP features above,
install the `LSP4IJ <https://plugins.jetbrains.com/plugin/23257-lsp4ij>`_
plugin and register ``.venv/bin/types-for-jinja-lsp`` (already present after
``uv sync``) as a user-defined language server mapped to Jinja templates
(language ID ``jinja``). See also :ref:`pycharm integration`.
