# Document Anonymization System

## Overview

This project provides a system for **selective anonymization of sensitive data contained in scanned documents**.

The primary use case is processing scanned lists of people who have outstanding debts. The documents are typically received as PDF files containing scanned pages. The information is therefore not available as structured text or tables. It exists primarily as images embedded in the PDF.

A typical document may contain information such as:

- First name
- Family name
- Address or place of residence
- Debt amount
- Original creditor or company associated with the debt
- Other identifying information

The objective is to allow an authorized user to search for a specific person and generate a new version of the document in which:

- the selected person remains identifiable,
- all other people are anonymized,
- sensitive information belonging to the other people is hidden,
- the document remains visually understandable and usable.

## Business Context

The system is intended for organizations involved in debt management and debt collection.

A typical process looks like this:

```text
External company / creditor
        |
        v
List of debtors
        |
        v
Scanned PDF document
        |
        v
Document Anonymization System
        |
        +--> Search for person
        |
        +--> Identify person in document
        |
        +--> Preserve selected person
        |
        +--> Anonymize all other people
        |
        v
Anonymized PDF
```

The resulting document can then be used in situations where the information about the requested person needs to remain visible, while information about unrelated individuals must not be disclosed.

## Problem Statement

The source documents are frequently scanned PDFs rather than digitally generated documents.

For example, a page may visually contain a table:

```text
+----------------+----------------+----------------+----------+----------------+
| First name     | Family name    | Address        | Amount   | Creditor       |
+----------------+----------------+----------------+----------+----------------+
| John           | Smith          | London ...     | 1200.00  | Company A      |
| Anna           | Brown          | Warsaw ...     | 850.00   | Company B      |
| Peter          | Wilson         | Gdansk ...     | 2300.00  | Company C      |
+----------------+----------------+----------------+----------+----------------+
```

However, from the computer's perspective the PDF may effectively contain only an image:

```text
PDF
 |
 +-- Page 1
 |    |
 |    +-- Image
 |
 +-- Page 2
      |
      +-- Image
```

Consequently, conventional text search cannot reliably be used.

The system therefore needs to combine:

- PDF processing
- Image processing
- OCR
- Document layout analysis
- Entity recognition
- Search
- Spatial coordinate detection
- PDF redaction/anonymization

## Primary Use Case

### 1. Upload document

The user uploads a scanned PDF containing a list of debtors.

```text
User
 |
 v
Upload PDF
 |
 v
Document Processing
```

### 2. Process document

The system analyzes each page.

```text
PDF
 |
 v
Page images
 |
 v
OCR
 |
 v
Text + coordinates
 |
 v
Document structure
```

The important point is that OCR should not only return text.

The system should retain the **location of every detected text fragment**.

For example:

```json
{
  "text": "John",
  "page": 1,
  "boundingBox": {
    "x": 120,
    "y": 340,
    "width": 50,
    "height": 20
  }
}
```

This spatial information is essential for the anonymization stage.

### 3. Search for person

The user enters information such as:

```text
John Smith
```

The system searches the OCR representation of the document.

The result should identify:

- matching person,
- page number,
- location on the page,
- associated table row.

For example:

```text
Match found

Person: John Smith
Page: 3
Row: 17
```

### 4. Identify the target row

The system must determine which OCR elements belong to the same logical table row.

For example:

```text
John Smith | London 10 | 1,200 PLN | Company A
```

The system should represent this internally as a logical record:

```json
{
  "firstName": "John",
  "lastName": "Smith",
  "address": "London 10",
  "amount": "1200 PLN",
  "creditor": "Company A",
  "page": 3,
  "rowBoundingBox": {
    "x": 100,
    "y": 540,
    "width": 1200,
    "height": 45
  }
}
```

### 5. Anonymize all other people

Once the target person has been identified, the system determines which rows belong to other people.

All sensitive information associated with those rows is then anonymized.

Conceptually:

```text
Original document

John Smith       | London 10 | 1200 PLN | Company A
Anna Brown       | Warsaw 20 |  850 PLN | Company B
Peter Wilson     | Gdansk 5  | 2300 PLN | Company C
```

becomes:

```text
Anonymized document

John Smith       | London 10 | 1200 PLN | Company A
██████████████   | █████████ | ████████ | █████████
██████████████   | █████████ | ████████ | █████████
```

The selected person remains visible.

All other individuals are anonymized.

## Important Design Principle

The system should **not modify the original document**.

Instead:

```text
Original PDF
     |
     +--------------------+
     |                    |
     v                    v
OCR / Analysis       Original preserved
     |
     v
Anonymization instructions
     |
     v
New PDF
```

The source document should remain immutable.

The anonymized PDF should be generated as a separate artifact.

## Proposed Architecture

A high-level architecture could look like this:

```text
                         +----------------+
                         |      User      |
                         +-------+--------+
                                 |
                                 v
                         +----------------+
                         | Web Application|
                         +-------+--------+
                                 |
                    +------------+------------+
                    |                         |
                    v                         v
             Document Upload             Search Person
                    |                         |
                    v                         |
             +-------------+                  |
             | PDF Service |                  |
             +------+------+                  |
                    |                         |
                    v                         |
             +-------------+                  |
             | OCR Engine  |                  |
             +------+------+                  |
                    |                         |
                    v                         |
             +-------------+                  |
             | Document    |<-----------------+
             | Structure   |
             +------+------+ 
                    |
                    v
             +-------------+
             | Anonymization|
             | Engine       |
             +------+-------+
                    |
                    v
             +-------------+
             | Output PDF   |
             +-------------+
```

## Processing Pipeline

The processing pipeline should be separated into distinct stages.

### Stage 1. PDF ingestion

Input:

```text
document.pdf
```

Output:

```text
pages/
    page-001.png
    page-002.png
    page-003.png
```

### Stage 2. OCR

Each page is processed by an OCR engine.

The OCR result should contain:

- recognized text,
- confidence,
- page number,
- bounding box,
- optionally line and word relationships.

Example:

```json
{
  "page": 1,
  "words": [
    {
      "text": "John",
      "confidence": 0.98,
      "bbox": [120, 340, 170, 360]
    },
    {
      "text": "Smith",
      "confidence": 0.97,
      "bbox": [175, 340, 230, 360]
    }
  ]
}
```

### Stage 3. Document layout analysis

OCR alone is not sufficient.

The system needs to reconstruct the logical structure of the document.

For example:

```text
Page
 |
 +-- Header
 |
 +-- Table
      |
      +-- Row 1
      +-- Row 2
      +-- Row 3
      ...
```

The system should identify:

- table boundaries,
- columns,
- rows,
- individual cells,
- relationships between OCR elements.

### Stage 4. Entity extraction

The system should identify relevant fields such as:

```text
PERSON
ADDRESS
AMOUNT
COMPANY
```

The exact implementation can evolve.

Initially, deterministic rules may be sufficient.

Later, machine-learning or LLM-based extraction can be introduced if document variability requires it.

### Stage 5. Search index

The extracted information should be indexed so that the user does not need to search the original image directly every time.

For example:

```json
{
  "documentId": "123",
  "page": 3,
  "row": 17,
  "firstName": "John",
  "lastName": "Smith"
}
```

Searching for:

```text
John Smith
```

returns:

```text
Document: 123
Page: 3
Row: 17
```

### Stage 6. Anonymization

The anonymization engine receives:

```text
Document
+
Target person
```

and determines:

```text
Keep:
    Target person's row

Anonymize:
    All other personal data
```

The anonymization should preferably use **true PDF redaction**, rather than simply drawing a black rectangle over text.

This distinction is important.

A visual rectangle can leave the underlying text embedded in the PDF and potentially recoverable.

The output should therefore remove or securely redact the underlying content whenever technically possible.

## Security and Privacy

This system processes highly sensitive personal information.

Security must therefore be considered a first-class architectural requirement.

### Data minimization

Only process the information required for the task.

### Original document protection

The original document should not be modified.

Access to the original should be restricted.

### Temporary files

Temporary images and OCR results should have a defined lifecycle.

For example:

```text
Upload
   |
   v
Processing
   |
   v
Anonymized output
   |
   v
Temporary artifacts deleted
```

### Access control

Users should only be able to access documents they are authorized to process.

### Audit logging

Important operations should be auditable.

For example:

```text
User A
uploaded Document 123

User A
searched for "John Smith"

User A
generated anonymized Document 123

Timestamp: 2026-08-19 14:32
```

Audit logs should themselves avoid storing unnecessary sensitive information.

## Technology Areas

The implementation is intentionally technology-agnostic at this stage.

Potential components include:

### PDF processing

- PDF rendering
- PDF text extraction
- PDF redaction
- PDF generation

### OCR

Potential OCR engines include:

- Tesseract
- Azure AI Document Intelligence
- AWS Textract
- Google Document AI
- other OCR/layout models

For table-heavy documents, an OCR/document-intelligence solution capable of returning **bounding boxes and table structure** is preferable to plain OCR.

### Document analysis

Possible approaches:

```text
OCR
 +
Layout analysis
 +
Rule-based extraction
```

or, for more complex documents:

```text
OCR
 +
Layout model
 +
LLM-assisted extraction
```

The second approach should not be introduced automatically. Deterministic processing is preferable whenever the document structure is sufficiently predictable.

## MVP

The first version should deliberately be narrow.

### MVP scope

- Upload scanned PDF
- Convert pages to images
- Perform OCR
- Store OCR text and coordinates
- Search for first name / family name
- Display matching page
- Identify matching row
- Select target person
- Redact all other rows
- Generate anonymized PDF

### Example MVP flow

```text
                Upload PDF
                    |
                    v
              Render pages
                    |
                    v
                  OCR
                    |
                    v
          Extract text + coordinates
                    |
                    v
             Build table rows
                    |
                    v
             Search for person
                    |
                    v
            Select matching person
                    |
                    v
        Identify all other persons
                    |
                    v
             Apply redaction
                    |
                    v
          Generate anonymized PDF
```

## Non-Goals for MVP

The first version should not attempt to solve every possible document format.

The MVP does not need to support:

- arbitrary document layouts,
- handwritten documents,
- every possible language,
- perfect semantic understanding,
- automatic identification of every possible personal-data field,
- complex multi-document workflows.

The initial goal is to prove that one representative document format can be processed reliably.

## Key Technical Challenge

The hardest part of the project is **not OCR**.

The difficult problem is maintaining the relationship between:

```text
OCR text
      |
      v
Physical coordinates
      |
      v
Table cell
      |
      v
Table row
      |
      v
Person
      |
      v
Anonymization region
```

If this relationship is incorrect, the system could anonymize the wrong person or expose information that should have been removed.

Therefore, the system should treat **document geometry and row identification as first-class data**, rather than treating the OCR output as a simple text string.

## Example Internal Data Model

A possible domain model:

```text
Document
 |
 +-- Page
      |
      +-- Table
           |
           +-- Row
                |
                +-- Person
                |
                +-- Cells
                     |
                     +-- FirstName
                     +-- LastName
                     +-- Address
                     +-- Amount
                     +-- Creditor
```

Each relevant object should retain its coordinates in the original document.

Example:

```json
{
  "documentId": "doc-001",
  "page": 2,
  "table": 1,
  "row": 15,
  "person": {
    "firstName": "John",
    "lastName": "Smith"
  },
  "cells": [
    {
      "type": "firstName",
      "text": "John",
      "bbox": [100, 500, 150, 520]
    },
    {
      "type": "lastName",
      "text": "Smith",
      "bbox": [155, 500, 220, 520]
    }
  ],
  "rowBoundingBox": [90, 495, 1200, 525]
}
```

## Future Extensions

Once the basic pipeline works, the system could be extended with:

- fuzzy person search,
- duplicate detection,
- multiple matching people,
- document preview,
- manual correction of OCR,
- manual correction of row boundaries,
- support for multiple document templates,
- automatic PII classification,
- configurable anonymization policies,
- batch processing,
- confidence scoring,
- human approval before document release,
- integration with existing document-management systems.

## Success Criteria

The system should ultimately satisfy the following requirements:

1. A scanned PDF can be processed without manually converting it into a table.
2. A user can search for a person by name.
3. The system can locate the person on the original scanned page.
4. The system can identify the person's complete row.
5. The selected person remains visible.
6. Other people's sensitive information is anonymized.
7. The anonymized PDF preserves the original document structure and readability.
8. The original document remains unchanged.
9. The anonymized output cannot reveal the redacted information through PDF text extraction or similar trivial techniques.
10. The system provides sufficient auditability to determine who processed a document and when.

## Project Status

**Status: Initial project definition**

The first development milestone should focus on validating the following technical hypothesis:

> Given a representative scanned PDF containing a structured list of debtors, can the system reliably identify a requested person and securely redact all other persons while preserving the selected person's information?

If this hypothesis is validated, the project can then evolve into a production-grade document anonymization platform.