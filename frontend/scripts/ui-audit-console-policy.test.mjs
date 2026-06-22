import assert from 'node:assert/strict'
import test from 'node:test'

import { shouldIgnoreAuditConsoleMessage } from './ui-audit-console-policy.mjs'


test('ignores Chromium WebGL readPixels warnings created by canvas audit', () => {
  assert.equal(
    shouldIgnoreAuditConsoleMessage({
      type: 'warning',
      text: '[.WebGL-0x123]GL Driver Message (OpenGL, Performance, GL_CLOSE_PATH_NV, High): GPU stall due to ReadPixels',
    }),
    true,
  )
})


test('keeps application warnings and HTTP errors as release blockers', () => {
  assert.equal(
    shouldIgnoreAuditConsoleMessage({
      type: 'error',
      text: 'Failed to load resource: the server responded with a status of 404 (Not Found)',
    }),
    false,
  )
  assert.equal(
    shouldIgnoreAuditConsoleMessage({
      type: 'warning',
      text: 'React state update failed',
    }),
    false,
  )
})
