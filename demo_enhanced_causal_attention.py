#!/usr/bin/env python3
"""
Demonstration of Enhanced Causal Attention Head with I.J. Good's Weight of Evidence
Shows the sophisticated Bayesian causal reasoning capabilities
"""

import os
import logging
from causal_attention_enhanced import EnhancedCausalAttentionWrapper, WeightOfEvidenceCalculus

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demonstrate_weight_of_evidence():
    """Demonstrate the I.J. Good Weight of Evidence calculus"""
    print("🧠 I.J. GOOD'S WEIGHT OF EVIDENCE CALCULUS DEMONSTRATION")
    print("=" * 60)
    
    calc = WeightOfEvidenceCalculus()
    
    # Show available hypotheses
    print("\n📋 CAUSAL HYPOTHESES:")
    for name, hypothesis in calc.hypotheses.items():
        print(f"  • {name}: {hypothesis.description}")
        print(f"    Prior Probability: {hypothesis.prior_probability:.1%}")
    
    # Show evidence types
    print(f"\n🔍 EVIDENCE TYPES:")
    for evidence_type in calc.evidence_likelihoods.keys():
        print(f"  • {evidence_type}")
    
    # Calculate weights for nested loops evidence
    print(f"\n⚖️ WEIGHT OF EVIDENCE FOR 'nested_loops' EVIDENCE:")
    print("Format: W(Hypothesis:Evidence) = log[P(E|H) / P(E|¬H)]")
    print("-" * 50)
    
    evidence_type = 'nested_loops'
    weights = []
    
    for hypothesis in calc.hypotheses.keys():
        weight = calc.calculate_weight_of_evidence(evidence_type, hypothesis)
        weights.append((hypothesis, weight))
        
        p_e_h = calc.evidence_likelihoods[evidence_type][hypothesis]
        print(f"W({hypothesis}:{evidence_type}) = {weight:+.3f}")
        print(f"  P(nested_loops|{hypothesis}) = {p_e_h:.2f}")
    
    # Sort by weight
    weights.sort(key=lambda x: x[1], reverse=True)
    print(f"\n🏆 EVIDENCE STRENGTH RANKING:")
    for i, (hypothesis, weight) in enumerate(weights, 1):
        strength = "Strong +" if weight > 1 else "Moderate +" if weight > 0 else "Negative -"
        print(f"  {i}. {hypothesis}: {weight:+.3f} ({strength})")
    
    return calc

def demonstrate_code_analysis():
    """Demonstrate sophisticated code analysis"""
    print("\n\n🔍 SOPHISTICATED CODE ANALYSIS DEMONSTRATION")
    print("=" * 60)
    
    # Sample inefficient code
    test_code = """
def matrix_multiply(A, B):
    rows_A, cols_A = len(A), len(A[0])
    rows_B, cols_B = len(B), len(B[0])
    
    result = []
    for i in range(rows_A):
        row = []
        for j in range(cols_B):
            sum_val = 0
            for k in range(cols_A):
                sum_val += A[i][k] * B[k][j]  # Repeated calculation
            row.append(sum_val)
        result.append(row)
    
    return result

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)  # Inefficient recursion
"""
    
    print("📝 ANALYZING CODE:")
    print(test_code)
    
    # Initialize enhanced causal attention (requires API key for full demo)
    api_key = os.environ.get("GOOGLE_API_KEY", "demo_key")
    
    if api_key != "demo_key":
        try:
            enhanced_attention = EnhancedCausalAttentionWrapper(api_key)
            
            print("\n🎯 CAUSAL ANALYSIS RESULTS:")
            insights = enhanced_attention.get_causal_insights(test_code)
            print(insights)
            
            # Show detailed analysis
            analysis = enhanced_attention.analyze_code_causally(test_code)
            
            print(f"\n📊 DETAILED EVIDENCE BREAKDOWN:")
            for evidence in analysis['evidence_details']:
                print(f"  • {evidence['type']} (strength: {evidence['strength']:.2f})")
                print(f"    Location: lines {evidence['location'][0]}-{evidence['location'][1]}")
                print(f"    Context: {evidence['context']}")
                print()
            
            print(f"🏆 HYPOTHESIS RANKINGS:")
            for i, h in enumerate(analysis['hypothesis_rankings'][:3], 1):
                print(f"  {i}. {h['hypothesis']}: {h['probability']:.1%} probability")
            
        except Exception as e:
            print(f"⚠️ Cannot run full demo without valid API key: {e}")
            print("Set GOOGLE_API_KEY environment variable for complete demonstration")
    else:
        print("⚠️ Set GOOGLE_API_KEY environment variable for complete demonstration")
        print("Showing Weight of Evidence calculations only...")

def compare_approaches():
    """Compare enhanced vs basic causal attention"""
    print("\n\n⚖️ ENHANCED vs BASIC CAUSAL ATTENTION COMPARISON")
    print("=" * 60)
    
    print("📈 ENHANCED I.J. GOOD WEIGHT OF EVIDENCE APPROACH:")
    print("  ✅ Bayesian probability calculations")
    print("  ✅ Multiple hypothesis evaluation") 
    print("  ✅ AST-based code parsing")
    print("  ✅ Sophisticated evidence detection")
    print("  ✅ Quantified causal strength measures")
    print("  ✅ Posterior odds ranking")
    
    print("\n📉 BASIC HEURISTIC APPROACH:")
    print("  ⚠️ Simple pattern matching")
    print("  ⚠️ Single-factor analysis")
    print("  ⚠️ Text-based parsing only")
    print("  ⚠️ Limited evidence types")
    print("  ⚠️ No quantified reasoning")
    print("  ⚠️ No probabilistic framework")
    
    print(f"\n🎯 KEY ADVANTAGES OF ENHANCED APPROACH:")
    print("  • Mathematical rigor via I.J. Good's framework")
    print("  • Multiple competing hypotheses evaluated simultaneously")
    print("  • Evidence weights calculated using Bayesian inference")
    print("  • AST parsing for deeper code understanding")
    print("  • Quantified confidence in causal reasoning")

def main():
    """Main demonstration"""
    print("🚀 PROJECT PROMETHEUS v0.18")
    print("Enhanced Causal Attention Head Demonstration")
    print("Implementing I.J. Good's Weight of Evidence Calculus")
    print("=" * 70)
    
    try:
        # Demonstrate weight of evidence calculations
        calc = demonstrate_weight_of_evidence()
        
        # Demonstrate code analysis
        demonstrate_code_analysis()
        
        # Compare approaches
        compare_approaches()
        
        print(f"\n🎉 DEMONSTRATION COMPLETE!")
        print("The Enhanced Causal Attention Head successfully implements")
        print("sophisticated Bayesian causal reasoning for code optimization.")
        
    except Exception as e:
        logger.error(f"Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()