#!/usr/bin/env bats
# Tests for token-optimizer shell shim (bash/zsh)

load 'test_helper/bats-support/load'
load 'test_helper/bats-assert/load'

# Path to the shim
SHIM_PATH="$(dirname "$BATS_TEST_FILENAME")/../../token-optimizer/hook/shim.sh"

setup() {
    source "$SHIM_PATH"
    _TOKEN_OPTIMIZER_TURN=0
}

teardown() {
    unset -f wrap_agent
    unset -f _token_optimizer_estimate
    unset -f _token_optimizer_send
    unset -f _token_optimizer_is_agent
    unset -f token_optimizer_daemon_start
    unset -f token_optimizer_daemon_stop
    unset -f token_optimizer_daemon_status
    unset -f token_optimizer_tui
}

@test "shim defines wrap_agent function" {
    run type wrap_agent
    assert_success
    assert_output --partial "function"
}

@test "shim defines _token_optimizer_estimate function" {
    run type _token_optimizer_estimate
    assert_success
}

@test "_token_optimizer_estimate returns 0 for empty input" {
    run _token_optimizer_estimate ""
    assert_output "0"
}

@test "_token_optimizer_estimate estimates chars/4" {
    run _token_optimizer_estimate "hello world"
    assert_output "2"  # 11 chars / 4 = 2
}

@test "_token_optimizer_is_agent returns true for known agents" {
    run _token_optimizer_is_agent "opencode"
    assert_success
    run _token_optimizer_is_agent "claude"
    assert_success
    run _token_optimizer_is_agent "codex"
    assert_success
}

@test "_token_optimizer_is_agent returns false for unknown commands" {
    run _token_optimizer_is_agent "ls"
    assert_failure
    run _token_optimizer_is_agent "git"
    assert_failure
}

@test "wrap_agent passes through non-agent commands" {
    run wrap_agent echo "hello world"
    assert_success
    assert_output "hello world"
}

@test "wrap_agent preserves exit code for non-agent commands" {
    run wrap_agent false
    assert_failure
    assert_equal "$status" 1
}

@test "wrap_agent increments turn counter for agent commands" {
    # Mock the agent command to avoid actually running it
    function opencode() { echo "mock output"; }
    export -f opencode
    
    run wrap_agent opencode "test"
    assert_success
    assert_equal "$_TOKEN_OPTIMIZER_TURN" 1
    
    run wrap_agent opencode "test"
    assert_success
    assert_equal "$_TOKEN_OPTIMIZER_TURN" 2
}

@test "token_optimizer_daemon_status returns stopped when not running" {
    run token_optimizer_daemon_status
    assert_output "stopped"
}

# Helper to test _token_optimizer_send (requires daemon, so just test it doesn't crash)
@test "_token_optimizer_send doesn't crash when daemon unavailable" {
    run _token_optimizer_send '{"type": "ping"}'
    # Should not crash even if daemon is not running
    assert [ "$status" -eq 0 -o "$status" -eq 1 ]
}