# MCP Security Guidelines

> **Source**: Moved from CLAUDE.md § MCP Server Integration Guidelines
> **Load when**: Code uses MCP servers

When reviewing code that uses MCP servers, validate:

## Supabase MCP Server
- ✅ Only used with authenticated projects
- ✅ All database operations validated (schema, RLS, permissions)
- ✅ No direct SQL injection vulnerabilities
- ✅ Proper error handling for failed operations

## GitHub MCP Server
- ✅ Repository permissions respected
- ✅ Appropriate branch strategies followed
- ✅ No sensitive data in commit messages
- ✅ Conventional commits format used

## Cloudflare SSE Servers
- ✅ All SSE URLs validated (HTTPS only)
- ✅ Trusted domains only
- ✅ No credential leakage in stream data
- ✅ Proper error handling for stream failures

## Brave/Tavily Search Servers
- ✅ Rate-limit aware usage
- ✅ No authentication required (as expected)
- ✅ Search queries sanitized (no injection)
- ✅ Results validated before use

## General MCP Security
- ✅ Each server operates within TDD methodology
- ✅ Tests first, then implementation
- ✅ No execution of untrusted code from MCP responses
- ✅ Proper error boundaries around MCP calls
