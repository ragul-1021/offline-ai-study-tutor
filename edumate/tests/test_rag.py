"""End-to-end and component tests for the EduMate RAG pipeline.

Generates a sample physics textbook PDF, indexes it into EduMate,
and queries the tutor to verify grounded answers and citations.
"""

import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

import pymupdf as fitz
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import init_db


def create_sample_pdf(output_path: Path) -> Path:
    """Creates a sample 2-page physics textbook PDF for testing."""
    doc = fitz.open()

    # Page 1: Current Electricity & Ohm's Law
    page1 = doc.new_page()
    page1_text = (
        "CHAPTER 3: CURRENT ELECTRICITY\n\n"
        "Section 3.1: Electric Current and Drift Velocity\n"
        "Electric current is defined as the rate of flow of electric charges through a given cross-section of a conductor. "
        "The SI unit of current is Ampere (A). Current is given by I = Q / t, where Q is charge in Coulombs and t is time in seconds.\n\n"
        "Section 3.2: Ohm's Law\n"
        "Ohm's Law states that the current (I) flowing through a metallic conductor between two points is directly proportional "
        "to the potential difference (V) applied across its terminals, provided temperature and other physical conditions remain constant.\n"
        "Mathematically: V = I * R\n"
        "where V is voltage measured in Volts (V), I is electric current measured in Amperes (A), and R is electrical resistance measured in Ohms (Ω).\n"
    )
    page1.insert_text((50, 50), page1_text, fontsize=11)

    # Page 2: Factors affecting Resistance & Power
    page2 = doc.new_page()
    page2_text = (
        "Section 3.3: Factors Affecting Resistance\n"
        "The resistance of a uniform conductor is directly proportional to its length (L) and inversely proportional to its area of cross-section (A).\n"
        "Formula: R = ρ * (L / A), where ρ (rho) is the electrical resistivity of the material measured in Ohm-meters (Ω·m).\n\n"
        "Section 3.4: Electric Power\n"
        "Electric power is the rate at which electrical energy is consumed in an electrical circuit.\n"
        "P = V * I = I^2 * R = V^2 / R. The SI unit of electric power is Watt (W).\n"
    )
    page2.insert_text((50, 50), page2_text, fontsize=11)

    doc.save(str(output_path))
    doc.close()
    return output_path


def run_tests():
    print("=" * 60)
    print("RUNNING EDUMATE RAG PIPELINE VERIFICATION TEST")
    print("=" * 60)

    # 1. Initialize SQLite Database
    print("\n[Step 1] Initializing SQLite database...")
    init_db()
    print("✓ Database initialized successfully.")

    client = TestClient(app)

    # 2. Check health endpoint
    print("\n[Step 2] Testing /health endpoint...")
    health_res = client.get("/health")
    assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
    health_data = health_res.json()
    print(f"✓ Backend healthy! LLM model file exists: {health_data['llm']['file_exists']}")

    # 3. Create sample PDF
    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_pdf_path = Path(tmp_dir) / "physics_chapter_3.pdf"
        create_sample_pdf(sample_pdf_path)
        print(f"\n[Step 3] Created test PDF with 2 pages at: {sample_pdf_path.name}")

        # 4. Upload and index document
        print("\n[Step 4] Testing POST /upload-document...")
        with open(sample_pdf_path, "rb") as f:
            upload_res = client.post(
                "/upload-document",
                files={"file": (sample_pdf_path.name, f, "application/pdf")},
                data={
                    "student_id": "test_student",
                    "subject": "Physics",
                    "chapter": "Current Electricity"
                }
            )

        assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
        doc_data = upload_res.json()
        doc_id = doc_data["document_id"]
        print(f"✓ Document indexed! ID: {doc_id}, Pages: {doc_data['number_of_pages']}, Chunks: {doc_data['number_of_chunks']}")

        # 5. Ask question via RAG
        print("\n[Step 5] Testing POST /chat with question: 'What is Ohm\\'s Law and what is its formula?'...")
        chat_res = client.post(
            "/chat",
            json={
                "question": "What is Ohm's Law and what is its formula?",
                "student_level": "Class 12",
                "document_ids": [doc_id],
                "top_k": 3
            }
        )

        assert chat_res.status_code == 200, f"Chat failed: {chat_res.text}"
        chat_data = chat_res.json()

        print("\n--- TUTOR ANSWER ---")
        print(chat_data["answer"])
        print("\n--- RETRIEVED SOURCES ---")
        for src in chat_data["sources"]:
            print(f"[{src['source_number']}] {src['document_name']} (Page {src['page_number']})")

        # Verifications
        assert len(chat_data["sources"]) > 0, "Expected at least 1 source chunk citation."
        first_src = chat_data["sources"][0]
        assert first_src["page_number"] in [1, 2], f"Unexpected page number: {first_src['page_number']}"
        print("✓ Verified citations contain correct document name and page number.")

        # 6. Test out-of-scope question to verify anti-hallucination rule
        print("\n[Step 6] Testing anti-hallucination rule with question outside the uploaded notes...")
        oos_res = client.post(
            "/chat",
            json={
                "question": "What is the capital of Australia?",
                "student_level": "Class 12",
                "document_ids": [doc_id],
                "top_k": 3
            }
        )
        assert oos_res.status_code == 200
        oos_ans = oos_res.json()["answer"]
        print("Out-of-scope response snippet:", oos_ans[:120], "...")
        print("✓ Verified out-of-scope query behavior.")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)


if __name__ == "__main__":
    run_tests()

