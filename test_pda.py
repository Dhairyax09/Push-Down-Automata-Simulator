# StackScope - Unit Test Suite for PDA Simulation Logic
# Simple assertions, no external test runners required.
# No __init__.py is used in this project.

import json
from pda.pda_core import PushdownAutomaton, Transition
from pda.simulator import PDASimulator
from pda.diagram import generate_pda_dot
from pda.generator import generate_dpda_for_language, load_dpda_from_file, LANGUAGE_CATALOG

def get_an_bn_pda():
    return load_dpda_from_file("an_bn.json")

def get_balanced_parentheses_pda():
    return load_dpda_from_file("balanced_parentheses.json")


def test_validation():
    print("[1/8] Testing DPDA Validation Logic...")
    # 1. Valid DPDA
    pda = get_an_bn_pda()
    valid, errors = pda.validate()
    assert valid, f"Expected valid DPDA, got errors: {errors}"

    # 2. Duplicate transition
    pda_dup = PushdownAutomaton(
        name="Dup", states=["q0"], input_alphabet=["a"], stack_alphabet=["Z0"],
        initial_state="q0", initial_stack_symbol="Z0", final_states=["q0"]
    )
    pda_dup.add_transition("q0", "a", "Z0", "q0", ["Z0"])
    pda_dup.add_transition("q0", "a", "Z0", "q0", ["A"])
    valid, errors = pda_dup.validate()
    assert not valid
    assert any("Duplicate" in e for e in errors)

    # 3. Epsilon conflict
    pda_conf = PushdownAutomaton(
        name="Conf", states=["q0"], input_alphabet=["a"], stack_alphabet=["Z0"],
        initial_state="q0", initial_stack_symbol="Z0", final_states=["q0"]
    )
    pda_conf.add_transition("q0", "ε", "Z0", "q0", ["Z0"])
    pda_conf.add_transition("q0", "a", "Z0", "q0", ["Z0"])
    valid, errors = pda_conf.validate()
    assert not valid
    assert any("Non-deterministic choice" in e for e in errors)

    # 4. Unknown state in transition
    pda_bad = PushdownAutomaton(
        name="Bad", states=["q0"], input_alphabet=["a"], stack_alphabet=["Z0"],
        initial_state="q0", initial_stack_symbol="Z0", final_states=["q0"]
    )
    pda_bad.add_transition("q0", "a", "Z0", "q_unknown", ["Z0"])
    valid, errors = pda_bad.validate()
    assert not valid
    assert any("to_state 'q_unknown'" in e for e in errors)

    print("   -> DPDA validation tests passed successfully!")


def test_an_bn():
    print("[2/8] Testing Language: L = { a^n b^n | n >= 1 }...")
    pda = get_an_bn_pda()
    sim = PDASimulator(pda)

    # Valid strings
    for s in ["ab", "aabb", "aaabbb", "aaaabbbb"]:
        res = sim.run(s)
        assert res.is_accepted, f"Expected '{s}' to be ACCEPTED, got {res.status}"
        print(f"   [PASS] '{s}' -> ACCEPTED in {res.total_steps} steps")

    # Invalid strings
    for s in ["", "a", "b", "aab", "aabbb", "ba", "aba", "aabbc"]:
        res = sim.run(s)
        assert not res.is_accepted, f"Expected '{s}' to be REJECTED, got {res.status}"
        print(f"   [PASS] '{s}' -> REJECTED correctly ({res.reason})")


def test_balanced_parentheses():
    print("[3/8] Testing Language: Balanced Parentheses...")
    pda = get_balanced_parentheses_pda()
    sim = PDASimulator(pda)

    # Valid strings
    for s in ["", "()", "(())", "()()", "((()))", "(()())", "(()(()))"]:
        res = sim.run(s)
        disp = s if s else "epsilon"
        assert res.is_accepted, f"Expected '{disp}' to be ACCEPTED, got {res.status}"
        print(f"   [PASS] '{disp}' -> ACCEPTED in {res.total_steps} steps")

    # Invalid strings
    for s in ["(", ")", "(()", "())", ")(", "())(()"]:
        res = sim.run(s)
        assert not res.is_accepted, f"Expected '{s}' to be REJECTED, got {res.status}"
        print(f"   [PASS] '{s}' -> REJECTED correctly ({res.reason})")


def test_json_serialization():
    print("[4/8] Testing JSON Export / Import...")
    pda = get_an_bn_pda()
    json_str = pda.to_json()
    data = json.loads(json_str)
    assert data["name"] == pda.name
    assert len(data["transitions"]) == len(pda.transitions)

    # Roundtrip
    pda_restored = PushdownAutomaton.from_json(json_str)
    assert pda_restored.name == pda.name
    assert pda_restored.states == pda.states
    assert len(pda_restored.transitions) == len(pda.transitions)

    # Verify simulation on restored PDA
    sim = PDASimulator(pda_restored)
    assert sim.run("aabb").is_accepted
    assert not sim.run("aab").is_accepted
    print("   -> JSON roundtrip serialization verified!")


def test_loop_prevention():
    print("[5/8] Testing Infinite Loop Prevention...")
    pda = PushdownAutomaton(
        name="InfiniteLoop", states=["q0"], input_alphabet=["a"], stack_alphabet=["Z0"],
        initial_state="q0", initial_stack_symbol="Z0", final_states=["q0"]
    )
    # Loop on epsilon without consuming input or changing state
    pda.add_transition("q0", "ε", "Z0", "q0", ["Z0"])
    sim = PDASimulator(pda, max_steps=50)
    res = sim.run("a")
    assert not res.is_accepted
    assert "exceeded maximum step limit" in res.reason
    print("   -> Infinite loop detected and halted safely!")


def test_diagram_generation():
    print("[6/8] Testing Graphviz DOT Diagram Generation...")
    pda = get_an_bn_pda()
    dot_str = generate_pda_dot(pda, current_state="q1", active_transition=pda.transitions[2])
    assert "digraph PDA" in dot_str
    assert "shape=doublecircle" in dot_str  # final state q2
    assert "style=filled" in dot_str and '"q1"' in dot_str  # highlighted active state
    assert 'color="#D9534F"' in dot_str  # highlighted active transition edge
    print("   -> Graphviz DOT generation verified with active highlights!")


def test_language_generator():
    print("[7/8] Testing Automated Language-to-DPDA Generator...")
    # 1. Multiplier a^n b^2n
    pda_2n, _ = generate_dpda_for_language("a^n b^2n (n >= 1)")
    sim_2n = PDASimulator(pda_2n)
    assert sim_2n.run("abb").is_accepted
    assert sim_2n.run("aabbbb").is_accepted
    assert not sim_2n.run("ab").is_accepted

    # 2. Push a, Read b, Pop c: a^n b^m c^n
    pda_3sym, _ = generate_dpda_for_language("a^n b^m c^n (n, m >= 1)")
    sim_3sym = PDASimulator(pda_3sym)
    assert sim_3sym.run("abc").is_accepted
    assert sim_3sym.run("aabbcc").is_accepted
    assert not sim_3sym.run("aabbc").is_accepted
    assert not sim_3sym.run("ab").is_accepted

    # 3. Palindrome w c w^R
    pda_pal, _ = generate_dpda_for_language("w c w^R (over {a, b})")
    sim_pal = PDASimulator(pda_pal)
    assert sim_pal.run("aca").is_accepted
    assert sim_pal.run("abcba").is_accepted
    assert not sim_pal.run("abc").is_accepted
    assert not sim_pal.run("abcca").is_accepted

    # 4. Inequality a^n b^m (n != m)
    pda_neq, _ = generate_dpda_for_language("a^n b^m (n != m)")
    sim_neq = PDASimulator(pda_neq)
    assert sim_neq.run("aab").is_accepted
    assert sim_neq.run("abb").is_accepted
    assert not sim_neq.run("ab").is_accepted
    assert not sim_neq.run("aabb").is_accepted

    # 5. Sum relation a^n b^m c^(n+m)
    pda_sum, _ = generate_dpda_for_language("a^n b^m c^(n+m) (n, m >= 1)")
    sim_sum = PDASimulator(pda_sum)
    assert sim_sum.run("abcc").is_accepted
    assert sim_sum.run("aabbcccc").is_accepted
    assert not sim_sum.run("abc").is_accepted

    # 6. Mixed Brackets
    pda_brk, _ = generate_dpda_for_language("Mixed Brackets () and []")
    sim_brk = PDASimulator(pda_brk)
    assert sim_brk.run("([()])").is_accepted
    assert sim_brk.run("()[]").is_accepted
    assert not sim_brk.run("([)]").is_accepted

    # 7. Non-CFL and NPDA guards
    pda_guard, explanation = generate_dpda_for_language("a^n b^n c^n")
    assert pda_guard is None
    assert "Context-Sensitive" in explanation

    pda_npda, npda_exp = generate_dpda_for_language("is a palindrome")
    assert pda_npda is None
    assert "NPDA" in npda_exp

    print("   -> All generated DPDA language families passed!")


def test_edge_cases():
    print("[8/8] Testing Edge Cases & Robustness...")
    # 1. Empty string on language requiring n >= 1
    pda_req = get_an_bn_pda()
    sim_req = PDASimulator(pda_req)
    res_empty = sim_req.run("")
    assert not res_empty.is_accepted, "Empty string should be rejected for n >= 1"

    # 2. Empty string on language allowing n >= 0
    pda_opt, _ = generate_dpda_for_language("a^n b^n (n >= 0)")
    sim_opt = PDASimulator(pda_opt)
    res_opt_empty = sim_opt.run("")
    assert res_opt_empty.is_accepted, "Empty string should be accepted for n >= 0"

    # 3. Deep stack execution (50 a's followed by 50 b's)
    long_valid = "a" * 50 + "b" * 50
    res_deep = sim_req.run(long_valid)
    assert res_deep.is_accepted, "Deep stack a^50 b^50 should be accepted"

    # 4. Long unbalanced string
    long_invalid = "a" * 50 + "b" * 49
    res_unbal = sim_req.run(long_invalid)
    assert not res_unbal.is_accepted, "Unbalanced long string should be rejected"

    # 5. Invalid character in input
    res_invalid_char = sim_req.run("aab#b")
    assert not res_invalid_char.is_accepted
    assert "Invalid symbol" in res_invalid_char.reason

    print("   -> Edge cases and deep stack tests passed successfully!")


if __name__ == "__main__":
    print("=" * 60)
    print("STACKSCOPE PDA SIMULATOR LOGIC TEST SUITE")
    print("=" * 60)
    test_validation()
    test_an_bn()
    test_balanced_parentheses()
    test_json_serialization()
    test_loop_prevention()
    test_diagram_generation()
    test_language_generator()
    test_edge_cases()
    print("=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
