#!/usr/bin/env python3
import sys
import os

# Add the Onboarding_agent to path
sys.path.insert(0, r'c:\Users\r.petniunas\Downloads\AI\rpetni-AE.CAP.1.1\Onboarding_agent')

try:
    from backend.rag.initializer import load_internal_rules_documents
    
    # Load all internal rules documents
    docs = load_internal_rules_documents()
    
    # Find and print organization structure info
    for doc in docs:
        if 'org' in doc.metadata.get('source', '').lower():
            print(f"\n{'='*80}")
            print(f"Source: {doc.metadata.get('source')}")
            print(f"{'='*80}\n")
            print(doc.page_content)
            print(f"\n{'='*80}\n")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
