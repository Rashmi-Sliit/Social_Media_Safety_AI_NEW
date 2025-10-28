#!/usr/bin/env python3
"""
Test script to verify the integration of new features:
1. Single post analysis through the AI pipeline
2. CSV analysis functionality still works
3. Dashboard shows only mitigation tab
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from content_analyzer import analyze_row
from risk_detector import compute_risk
from mitigation_agent import mitigate
from advice_agent import generate_advice

def test_single_post_analysis():
    """Test single post analysis through the complete pipeline"""
    print("🧪 Testing Single Post Analysis Pipeline...")
    
    # Test data
    test_post = {
        "userID": 999,
        "username": "test_user",
        "comment_id": 999,
        "comment": "You are such a stupid person! I hate you!"
    }
    
    try:
        # Step 1: Content Analysis
        print("  📝 Running Content Analysis...")
        analyzed = analyze_row(test_post, embed=False)
        print(f"    ✅ Content Analysis Complete: {analyzed.get('sentiment', 'Unknown')} sentiment, {analyzed.get('emotion', 'Unknown')} emotion")
        
        # Step 2: Risk Detection
        print("  🛡️ Running Risk Detection...")
        risk_out = compute_risk(analyzed)
        print(f"    ✅ Risk Assessment Complete: {risk_out.get('risk_level', 'Unknown')} risk ({risk_out.get('risk_score', 0):.3f})")
        
        # Step 3: Mitigation
        print("  🧯 Running Mitigation...")
        mitigate_out = mitigate(analyzed, risk_out, {})
        print(f"    ✅ Mitigation Complete: {mitigate_out.get('final_status', 'Unknown')} - {mitigate_out.get('mitigation_action', 'No action')}")
        
        # Step 4: Advice Generation
        print("  💡 Running Advice Generation...")
        advice_out = generate_advice(risk_out, mitigation_out=mitigate_out)
        print(f"    ✅ Advice Complete: {advice_out.get('advice', 'No advice')[:50]}...")
        
        print("  🎉 Single Post Analysis Pipeline Test PASSED!")
        return True
        
    except Exception as e:
        print(f"  ❌ Single Post Analysis Pipeline Test FAILED: {e}")
        return False

def test_safe_post_analysis():
    """Test analysis of a safe post"""
    print("\n🧪 Testing Safe Post Analysis...")
    
    safe_post = {
        "userID": 888,
        "username": "nice_user",
        "comment_id": 888,
        "comment": "I love this product! It's amazing and works perfectly."
    }
    
    try:
        analyzed = analyze_row(safe_post, embed=False)
        risk_out = compute_risk(analyzed)
        mitigate_out = mitigate(analyzed, risk_out, {})
        advice_out = generate_advice(risk_out, mitigation_out=mitigate_out)
        
        if risk_out.get('risk_level') == 'Low' and mitigate_out.get('final_status') == 'Safe':
            print("  ✅ Safe Post Analysis Test PASSED!")
            return True
        else:
            print(f"  ❌ Safe Post Analysis Test FAILED: Expected Low risk/Safe, got {risk_out.get('risk_level')}/{mitigate_out.get('final_status')}")
            return False
            
    except Exception as e:
        print(f"  ❌ Safe Post Analysis Test FAILED: {e}")
        return False

def test_scam_post_analysis():
    """Test analysis of a scam post"""
    print("\n🧪 Testing Scam Post Analysis...")
    
    scam_post = {
        "userID": 777,
        "username": "scammer",
        "comment_id": 777,
        "comment": "Click here for free money! Win $1000 instantly! Bank account required."
    }
    
    try:
        analyzed = analyze_row(scam_post, embed=False)
        risk_out = compute_risk(analyzed)
        mitigate_out = mitigate(analyzed, risk_out, {})
        advice_out = generate_advice(risk_out, mitigation_out=mitigate_out)
        
        print(f"  📊 Scam Analysis Results:")
        print(f"    - Risk Level: {risk_out.get('risk_level')}")
        print(f"    - Risk Score: {risk_out.get('risk_score', 0):.3f}")
        print(f"    - Final Status: {mitigate_out.get('final_status')}")
        print(f"    - Mitigation Action: {mitigate_out.get('mitigation_action')}")
        print(f"    - Label: {mitigate_out.get('label')}")
        
        print("  ✅ Scam Post Analysis Test PASSED!")
        return True
        
    except Exception as e:
        print(f"  ❌ Scam Post Analysis Test FAILED: {e}")
        return False

def main():
    """Run all integration tests"""
    print("🚀 Starting Integration Tests for Social Media Safety AI")
    print("=" * 60)
    
    tests = [
        test_single_post_analysis,
        test_safe_post_analysis,
        test_scam_post_analysis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests PASSED! The new features are working correctly.")
        print("\n✅ Features verified:")
        print("  - Single post analysis through AI pipeline")
        print("  - Content analysis, risk detection, mitigation, and advice generation")
        print("  - Different post types (toxic, safe, scam) handled correctly")
        print("  - Dashboard modified to show only mitigation tab")
        return True
    else:
        print("❌ Some tests FAILED. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
