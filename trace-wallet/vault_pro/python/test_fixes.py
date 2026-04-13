"""
Test Suite for Vault Pro Fixes
Tests all the improvements made to ensure code reliability
"""
import sys
import os
import json
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import DatabaseService, VaultTransaction, VaultPerson, PairedDevice
from parser import parser, RegexParserService
from sidecar import Sidecar

def test_database_thread_safety():
    """Test thread-safe database operations"""
    print("\n=== Testing Database Thread Safety ===")
    
    # Create a temp database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize database
        db = DatabaseService(db_path)
        
        # Test concurrent writes from multiple threads
        errors = []
        results = []
        
        def add_transaction(thread_id):
            try:
                tx = VaultTransaction(
                    raw_text=f"Test transaction from thread {thread_id}",
                    amount=100.0 + thread_id,
                    date=datetime.now().isoformat(),
                    category="Test"
                )
                tx_id = db.add_transaction(tx)
                results.append(tx_id)
            except Exception as e:
                errors.append(str(e))
        
        # Spawn multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=add_transaction, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 10, f"Expected 10 transactions, got {len(results)}"
        
        # Verify all transactions exist
        all_tx = db.get_all_transactions()
        assert len(all_tx) == 10, f"Expected 10 transactions in DB, got {len(all_tx)}"
        
        print("[PASS] Database thread safety test passed")
        
    finally:
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass

def test_database_error_handling():
    """Test database error handling"""
    print("\n=== Testing Database Error Handling ===")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = DatabaseService(db_path)
        
        # Test invalid transaction ID
        result = db.get_transaction(99999)
        assert result is None, "Should return None for non-existent transaction"
        
        # Test search with None query (edge case)
        result = db.search_transactions("")
        assert isinstance(result, list), "Search should return a list"
        
        # Test statistics with empty database
        stats = db.get_statistics()
        assert 'error' not in stats or stats.get('error') is None, "Statistics should work"
        
        print("[PASS] Database error handling test passed")
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass

def test_parser_amount_extraction():
    """Test parser amount extraction from various formats"""
    print("\n=== Testing Parser Amount Extraction ===")
    
    test_cases = [
        ("Your CBE account debited with ETB 5,000. Current balance is ETB 45,678.90", 5000.0),
        ("Transferred ETB 1,234.56 to John Doe", 1234.56),
        ("Received ETB 100 from Jane", 100.0),
        ("Paid ETB 50.75 for groceries", 50.75),
        ("ETB 1,000.00 charged", 1000.0),
    ]
    
    for sms, expected_amount in test_cases:
        result = parser.process_raw_transaction(sms)
        if result.amount is not None:
            assert abs(result.amount - expected_amount) < 0.01, \
                f"Failed for '{sms}': expected {expected_amount}, got {result.amount}"
    
    print("[PASS] Parser amount extraction test passed")

def test_parser_bank_detection():
    """Test parser bank detection"""
    print("\n=== Testing Parser Bank Detection ===")
    
    test_cases = [
        ("CBE account debited", "CBE"),
        ("Telebirr payment received", "Telebirr"),
        ("BOA transfer completed", "BOA"),
        ("Some random message", "Other"),
    ]
    
    for sms, expected_bank in test_cases:
        result = parser.process_raw_transaction(sms)
        assert result.bank == expected_bank, \
            f"Failed for '{sms}': expected {expected_bank}, got {result.bank}"
    
    print("[PASS] Parser bank detection test passed")

def test_sidecar_validation():
    """Test sidecar input validation"""
    print("\n=== Testing Sidecar Input Validation ===")
    
    sidecar = Sidecar()
    
    # Test invalid transaction (missing amount)
    try:
        sidecar.add_transaction({"raw_text": "test"})
        assert False, "Should have raised ValueError for missing amount"
    except ValueError as e:
        assert "amount" in str(e).lower()
    
    # Test invalid transaction (invalid amount)
    try:
        sidecar.add_transaction({"amount": "not_a_number"})
        assert False, "Should have raised ValueError for invalid amount"
    except ValueError:
        pass
    
    # Test delete with invalid ID
    try:
        sidecar.delete_transaction(None)
        assert False, "Should have raised ValueError for None ID"
    except ValueError:
        pass
    
    # Test person without name
    try:
        sidecar.add_person({"aliases": ["test"]})
        assert False, "Should have raised ValueError for missing name"
    except ValueError:
        pass
    
    print("[PASS] Sidecar validation test passed")

def test_import_export():
    """Test import/export functionality with duplicate detection"""
    print("\n=== Testing Import/Export ===")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    export_path = db_path + '.export.json'
    
    try:
        db = DatabaseService(db_path)
        
        # Add test data
        tx = VaultTransaction(
            raw_text="Test transaction for export",
            amount=500.0,
            date=datetime.now().isoformat(),
            category="Test"
        )
        db.add_transaction(tx)
        
        person = VaultPerson(
            name="Test Person",
            aliases=["Test", "TP"],
            monthly_fee=100.0
        )
        db.add_person(person)
        
        # Test export
        success = db.export_to_json(export_path)
        assert success, "Export should succeed"
        assert os.path.exists(export_path), "Export file should exist"
        
        # Test import with duplicate detection
        result = db.import_from_json(export_path)
        assert 'errors' in result, "Import result should have errors field"
        # Should skip duplicates, so count should be 0
        assert result['transactions'] == 0, "Should skip duplicate transactions"
        assert result['people'] == 0, "Should skip duplicate people"
        
        print("[PASS] Import/Export test passed")
        
    finally:
        try:
            os.unlink(db_path)
            if os.path.exists(export_path):
                os.unlink(export_path)
        except:
            pass

def test_data_consistency():
    """Test data consistency between operations"""
    print("\n=== Testing Data Consistency ===")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = DatabaseService(db_path)
        
        # Add person
        person = VaultPerson(
            name="John Doe",
            aliases=["John", "JD"],
            monthly_fee=50.0,
            total_transactions=10,
            total_amount=5000.0
        )
        person_id = db.add_person(person)
        
        # Retrieve and verify
        people = db.get_all_people()
        assert len(people) == 1
        retrieved = people[0]
        assert retrieved.name == "John Doe"
        assert retrieved.aliases == ["John", "JD"]
        assert retrieved.monthly_fee == 50.0
        
        # Update and verify
        retrieved.monthly_fee = 75.0
        db.update_person(retrieved)
        
        people = db.get_all_people()
        assert people[0].monthly_fee == 75.0
        
        print("[PASS] Data consistency test passed")
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass

def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("VAULT PRO FIXES VERIFICATION TEST SUITE")
    print("=" * 50)
    
    tests = [
        test_database_thread_safety,
        test_database_error_handling,
        test_parser_amount_extraction,
        test_parser_bank_detection,
        test_sidecar_validation,
        test_import_export,
        test_data_consistency,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"[FAIL] {test.__name__} FAILED: {e}")
    
    print("\n" + "=" * 50)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 50)
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
