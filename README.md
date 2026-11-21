# V91 recovery control

This repository holds a disabled, credential-free recovery controller and a public CA certificate. A verified manual run stops with exit 66. The workflow performs no database operations.

Dispatch is restricted to the reviewed `main` commit and the `alpine-v91-restore` environment. Keep the environment empty and require an independent reviewer before testing its approval gate.

Pull requests run credential-free checks from the base revision. The current policy rejects changes to the controller, tests, certificate and manifest. Review workflow changes independently of the required check.
