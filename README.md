# Transaction Parser

## Overview

Transaction Parser is an AI-powered add-on for ERPNext that automatically extracts data from PDFs and creates draft documents (Sales Order / Purchase Invoice) . It supports multiple document types and regions, making it easier to digitize and process business documents.

## Features

* **AI-Powered Extraction**: Uses advanced AI models (OpenAI, DeepSeek, Google Gemini) to extract structured data from PDFs  
* **Multi-Document Support**: Handles Sales Orders and Purchase Invoices (Expenses)  
* **Regional Support**: Special handling for India-specific requirements (GSTIN, PAN, HSN codes)  
* **Email Integration**: Automatically processes documents from incoming emails  
* **Customizable Schemas**: Flexible field mapping and custom schema support  
* **Smart Item Matching**: Automatically matches items from previous invoices

## Configuration

1\. Enable Transaction Parser  
Navigate to **Transaction Parser Settings** and configure:

1. **Enable**: Check to activate the app
   
   <img width="514" height="194" alt="image" src="https://github.com/user-attachments/assets/b1fd29ad-fa14-42b6-835b-77dfab34ca7e" />


2\. **Default AI Model**: Select from available models:  
   * DeepSeek Chat  
   * DeepSeek Reasoner  
   * OpenAI gpt-4o  
   * OpenAI gpt-4o-mini  
   * OpenAI gpt-5  
   * Google Gemini 2.5 pro  
   * Google Gemini 2.5 flash
  
  <img width="773" height="291" alt="image" src="https://github.com/user-attachments/assets/fc40bea1-1e11-4ef3-bcdf-f6c1db8585c8" />



3\. API Keys Setup

Add your API keys for the AI services:

| Service Provider | Models Supported |
| :---- | :---- |
| OpenAI | gpt-4o, gpt-4o-mini , gpt-5 |
| DeepSeek | deepseek-chat, deepseek-reasoner |
| Google | gemini 2.5 pro, gemini 2.5 flash |

  <img width="800" height="148" alt="image" src="https://github.com/user-attachments/assets/77f30bd8-59a1-4b66-8bf4-964bc2347ce4" />



4\. Email Configuration (Optional)  
To automatically process documents from emails:

1. **Parse Incoming Emails**: Enable email processing  
2. **Incoming Email Accounts**: Configure which email accounts to monitor  
3. **Party Emails**: Map email addresses to specific customers/suppliers

   <img width="783" height="347" alt="image" src="https://github.com/user-attachments/assets/b6395615-b3ca-434a-ab91-c6733a11a62c" />



5\. Transaction Configuration

* **Invoice Lookback Count**: Number of past invoices to consider for item matching (default: 5\)

  <img width="575" height="143" alt="image" src="https://github.com/user-attachments/assets/98acb8af-2d6e-482c-976b-36a507c97e14" />


## Usage

### Manual Document Processing

1. Navigate to Sales Order or Purchase Invoice list view  
2. Click on **Actions → Parse Sales Order/Expense Invoice**  
3. Upload your PDF file  
4. Select:  
   * **AI Model**: Choose the AI model to use  
   * **Country**: Select India or Other  
   * **Page Limit**: (Optional) Limit pages to process  
5. Click **Submit**


  https://github.com/user-attachments/assets/6c70d018-1de2-40de-97e2-1c1c9b583a11


The system will:

* Extract text from the PDF  
* Send it to the AI model for processing  
* Create a draft document with extracted data  
* Attach the original PDF to the created document

### Automatic Email Processing

When enabled, the system automatically:

1. Monitors configured email accounts  
2. Extracts PDF attachments from emails  
3. Processes them based on sender and configuration  
4. Creates draft documents

## Model Comparison

| Model | Provider | Best For | Speed | Cost |
| :---- | :---- | :---- | :---- | :---- |
| gpt-5 | OpenAI | State-of-the-art accuracy, complex multi-page documents | Medium | High |
| gpt-4o | OpenAI | Complex documents, high accuracy | Medium | Medium-High |
| gpt-4o-mini | OpenAI | Cost-effective, good accuracy | Fast | Low |
| gemini-2.5-pro | Google | Advanced reasoning, large context window | Medium | Medium |
| gemini-2.5-flash | Google | Fast processing, bulk documents | Very Fast | Low |
| deepseek-chat | DeepSeek | General purpose extraction | Fast | Low |
| deepseek-reasoner | DeepSeek | Complex reasoning tasks | Slow | Medium |

## India-Specific Features

The Transaction Parser app includes robust support for Indian business requirements through integration with the **India Compliance** app. These features enable automatic handling of GST regulations, Indian business identifiers, and region-specific validation requirements.

### Prerequisites

* **India Compliance App**: Must be installed for India-specific features to work

### India-Specific AI Model Enhancements

**Enhanced Data Extraction** - When processing documents with the India region selected, the AI models are enhanced to extract:

1. **GST Identification Numbers (GSTIN)**
2. **Permanent Account Numbers (PAN)**
3. **HSN/SAC Codes**
4. **Tax Components**

### Automatic Supplier Creation

GSTIN-Based Supplier Creation  
When enabled in settings, the system can automatically create suppliers:

1. **Configuration**
   * Enable "Auto Create Supplier" in Transaction Parser Settings
   * Requires valid GSTIN in the invoice

## License

[GNU General Public License (v3)](https://github.com/resilient-tech/transaction-parser/blob/version-15/license.txt)
