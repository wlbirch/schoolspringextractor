import pandas as pd
import re
import argparse
import sys
import csv
from typing import Dict, Optional, List

class JobDataExtractor:
    """
    Extracts structured data from job posting text and transforms it into standardized format.
    Version 6.1: Enhanced diagnostics to identify missing rows.
    """
    
    def __init__(self):
        # Comprehensive character replacements for encoding issues
        self.char_replacements = {
            'â€™': "'",
            'â€œ': '"',
            'â€': '"',
            'â€"': '-',
            'â€"': '-',
            'â€¢': '•',
            'Ã¢â‚¬â„¢': "'",
            'Ã¢â‚¬"': '"',
            'Ã¢â‚¬Å"': '"',
            'Ã¢â‚¬': '"',
            'Ã¢â‚¬Â¢': '•',
            'Ã‚': '',
            '&amp;': '&',
            '&nbsp;': ' ',
            '\xa0': ' ',
            '\u2019': "'",
            '\u2018': "'",
            '\u201c': '"',
            '\u201d': '"',
            '\u2013': '-',
            '\u2014': '-',
            '\u2022': '•',
            'ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢': "'",
            'Ã¢â‚¬â€¹': '',
            'ÃƒÂ¢Ã¢â€šÂ¬': '"',
        }
    
    def fix_encoding_issues(self, text: str) -> str:
        """Fix common encoding issues in text."""
        if not text:
            return ""
        
        # Apply character replacements
        for bad_char, good_char in self.char_replacements.items():
            text = text.replace(bad_char, good_char)
        
        return text
    
    def remove_leading_bullets_and_numbers(self, text: str) -> str:
        """Remove leading bullets, dashes, asterisks, and numbers from text."""
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove various bullet types and numbering
            line = re.sub(r'^[-•*◦▪▫◆◇→⇒·]\s*', '', line)
            line = re.sub(r'^\d+[.)]\s*', '', line)
            line = re.sub(r'^[a-zA-Z][.)]\s*', '', line)
            line = re.sub(r'^\([a-zA-Z0-9]+\)\s*', '', line)
            line = re.sub(r'^[IVXivx]+[.)]\s*', '', line)  # Roman numerals
            
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Fix encoding first
        text = self.fix_encoding_issues(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # Remove bullets and numbering
        text = self.remove_leading_bullets_and_numbers(text)
        
        # Final cleanup
        text = re.sub(r'  +', ' ', text)
        text = text.strip()
        
        return text
    
    def extract_position_summary(self, job_description: str) -> str:
        """Extract position summary with multiple strategies."""
        job_description = self.fix_encoding_issues(job_description)
        
        # Strategy 1: Look for explicit summary sections
        summary_patterns = [
            r'(?i)(?:POSITION\s+)?SUMMARY:?\s*(.*?)(?=\n\s*(?:EDUCATION|EXPERIENCE|QUALIFICATIONS|ESSENTIAL|RESPONSIBILITIES|[A-Z\s]+:|$))',
            r'(?i)JOB\s+GOAL:?\s*(.*?)(?=\n\s*(?:EDUCATION|EXPERIENCE|QUALIFICATIONS|ESSENTIAL|[A-Z\s]+:|$))',
            r'(?i)OVERVIEW:?\s*(.*?)(?=\n\s*(?:EDUCATION|EXPERIENCE|QUALIFICATIONS|ESSENTIAL|[A-Z\s]+:|$))',
            r'(?i)JOB\s+SUMMARY:?\s*(.*?)(?=\n\s*(?:EDUCATION|EXPERIENCE|QUALIFICATIONS|ESSENTIAL|[A-Z\s]+:|$))',
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, job_description, re.DOTALL)
            if match and match.group(1).strip():
                summary = self.clean_text(match.group(1))
                if len(summary) > 30:  # Ensure it's substantial
                    return summary
        
        # Strategy 2: Look for descriptive text at the beginning
        paragraphs = job_description.split('\n\n')
        for paragraph in paragraphs[:3]:
            paragraph = paragraph.strip()
            if len(paragraph) > 50 and not re.match(r'^[A-Z\s]+:', paragraph):
                if any(word in paragraph.lower() for word in ['responsible for', 'position', 'role', 'duties']):
                    return self.clean_text(paragraph)
        
        return ""
    
    def extract_education(self, job_description: str) -> str:
        """Extract education requirements."""
        job_description = self.fix_encoding_issues(job_description)
        
        education_items = []
        
        # Look for education section headers
        education_patterns = [
            r'(?i)EDUCATION\s+(?:REQUIREMENTS?|AND[/\s]OR\s+EXPERIENCE)?:?\s*(.*?)(?=\n\s*(?:EXPERIENCE|LICENSES|CERTIFICATES|KNOWLEDGE|SKILLS|ESSENTIAL|SUPERVISORY|QUALIFICATIONS|PHYSICAL|$))',
            r'(?i)QUALIFICATIONS?:?\s*(?:EDUCATION:?\s*)?(.*?)(?=\n\s*(?:EXPERIENCE|LICENSES|$))',
            r'(?i)MINIMUM\s+QUALIFICATIONS?:?\s*(.*?)(?=\n\s*(?:EXPERIENCE|LICENSES|$))',
        ]
        
        for pattern in education_patterns:
            match = re.search(pattern, job_description, re.DOTALL)
            if match:
                section_text = match.group(1)
                
                # Look for education-specific content
                lines = section_text.split('\n')
                for line in lines:
                    line = line.strip()
                    # Check for education keywords and exclude experience
                    if re.search(r'(?i)(?:bachelor|master|phd|doctorate|associate|degree|diploma|ged|high school|education)', line):
                        if not re.search(r'(?i)\d+\s+(?:years?|months?)\s+(?:of\s+)?(?:experience|working)', line):
                            education_items.append(self.clean_text(line))
                            break
                
                if education_items:
                    break
        
        # Look for inline education requirements if no section found
        if not education_items:
            inline_patterns = [
                r'(?i)((?:bachelor|master|phd|associate)(?:\'s|s)?\s+degree[^.;]*[.;]?)',
                r'(?i)(high\s+school\s+(?:diploma|degree)\s+or\s+(?:ged|equivalent)[^.;]*[.;]?)',
                r'(?i)(minimum\s+(?:of\s+)?(?:a\s+)?(?:bachelor|master|associate)[^.;]*[.;]?)',
            ]
            
            for pattern in inline_patterns:
                matches = re.findall(pattern, job_description)
                for match in matches:
                    clean_match = self.clean_text(match)
                    if clean_match and len(clean_match) > 10:
                        education_items.append(clean_match)
                        break
                if education_items:
                    break
        
        return education_items[0] if education_items else ""
    
    def extract_work_experience(self, job_description: str) -> str:
        """Extract work experience requirements."""
        job_description = self.fix_encoding_issues(job_description)
        
        experience_items = []
        
        # Look for experience patterns
        experience_patterns = [
            r'(?i)(?:WORK\s+)?EXPERIENCE\s*(?:REQUIREMENTS?)?:?\s*(.*?)(?=\n\s*(?:EDUCATION|LICENSES|CERTIFICATES|KNOWLEDGE|SKILLS|ESSENTIAL|$))',
            r'(?i)(\d+\s*(?:\+|\-|or\s+more)?\s*(?:years?|yrs?)\s+(?:of\s+)?[^.;]*?experience[^.;]*[.;]?)',
            r'(?i)((?:minimum|at\s+least|must\s+have|requires?)\s+\d+\s+(?:years?|yrs?)[^.;]*?experience[^.;]*[.;]?)',
            r'(?i)(previous\s+experience[^.;]*[.;]?)',
        ]
        
        for pattern in experience_patterns:
            matches = re.findall(pattern, job_description, re.DOTALL)
            for match in matches:
                if match:
                    clean_match = self.clean_text(match)
                    # Ensure it mentions experience and has numbers/timeframes
                    if 'experience' in clean_match.lower() and (re.search(r'\d+', clean_match) or 'previous' in clean_match.lower()):
                        # Make sure it's not about education
                        if not any(edu in clean_match.lower() for edu in ['bachelor', 'master', 'degree', 'diploma']):
                            experience_items.append(clean_match)
                            break
            if experience_items:
                break
        
        # Look in combined sections if nothing found
        if not experience_items:
            combined_pattern = r'(?i)EDUCATION\s+AND[/\s]OR\s+EXPERIENCE:?\s*(.*?)(?=\n\s*(?:CERTIFICATES|ESSENTIAL|SUPERVISORY|$))'
            match = re.search(combined_pattern, job_description, re.DOTALL)
            if match:
                section_text = match.group(1)
                sentences = re.split(r'[.;]', section_text)
                for sentence in sentences:
                    if re.search(r'(?i)\d+\s+(?:years?|yrs?)\s+(?:of\s+)?.*?experience', sentence):
                        experience_items.append(self.clean_text(sentence))
                        break
        
        return experience_items[0] if experience_items else ""
    
    def extract_essential_functions(self, job_description: str) -> str:
        """Extract essential functions/duties."""
        job_description = self.fix_encoding_issues(job_description)
        
        functions = []
        
        # Look for various section headers
        function_patterns = [
            r'(?i)ESSENTIAL\s+(?:DUTIES\s+AND\s+)?(?:FUNCTIONS|RESPONSIBILITIES)[^:]*:?\s*(.*?)(?=\n\s*(?:SUPERVISORY|QUALIFICATIONS?|CERTIFICATES?|COMMUNICATION|PHYSICAL|WORK\s+ENVIRONMENT|EDUCATION|EXPERIENCE|$))',
            r'(?i)(?:KEY\s+|PRIMARY\s+|MAJOR\s+)?RESPONSIBILITIES[^:]*:?\s*(.*?)(?=\n\s*(?:QUALIFICATIONS?|REQUIREMENTS?|EDUCATION|EXPERIENCE|SUPERVISORY|$))',
            r'(?i)(?:PRIMARY\s+|MAJOR\s+)?DUTIES[^:]*:?\s*(.*?)(?=\n\s*(?:QUALIFICATIONS?|REQUIREMENTS?|EDUCATION|EXPERIENCE|$))',
            r'(?i)JOB\s+DUTIES[^:]*:?\s*(.*?)(?=\n\s*(?:QUALIFICATIONS?|REQUIREMENTS?|EDUCATION|EXPERIENCE|$))',
            r'(?i)SUPERVISORY\s+RESPONSIBILITIES:?\s*(.*?)(?=\n\s*(?:QUALIFICATIONS?|CERTIFICATES?|EDUCATION|$))',
        ]
        
        for pattern in function_patterns:
            match = re.search(pattern, job_description, re.DOTALL)
            if match and match.group(1).strip():
                section_text = match.group(1)
                
                # Clean and split the text
                section_text = self.clean_text(section_text)
                
                # Split by various delimiters
                items = re.split(r'[\n;]|(?<=\.)\s+(?=[A-Z])', section_text)
                
                for item in items:
                    item = item.strip()
                    if item and len(item) > 20:  # Only substantial items
                        functions.append(item)
                
                if functions:
                    break
        
        # If no explicit section found, look for bulleted lists
        if not functions:
            lines = job_description.split('\n')
            in_duties_section = False
            
            for line in lines:
                line_stripped = line.strip()
                
                # Check if we're entering a duties section
                if re.search(r'(?i)(?:responsibilities|duties|functions)', line_stripped):
                    in_duties_section = True
                    continue
                
                # Stop at next major section
                if in_duties_section and re.match(r'^[A-Z\s]+:', line_stripped):
                    break
                
                # Collect bulleted items
                if re.match(r'^[-•*]\s*', line_stripped) or in_duties_section:
                    cleaned = self.clean_text(line_stripped)
                    if cleaned and len(cleaned) > 20:
                        functions.append(cleaned)
        
        # Return up to 15 functions, joined with newlines
        if functions:
            return '\n'.join(functions[:15])
        
        return ""
    
    def extract_licenses_certifications(self, job_description: str) -> str:
        """Extract licenses and certifications."""
        job_description = self.fix_encoding_issues(job_description)
        
        cert_items = []
        
        # Look for certification sections
        cert_patterns = [
            r'(?i)(?:CERTIFICATES?|LICENSES?|CERTIFICATIONS?|REGISTRATIONS?)[^:]*:?\s*(.*?)(?=\n\s*(?:COMMUNICATION|MATHEMATICAL|REASONING|TECHNOLOGY|OTHER|PHYSICAL|LANGUAGE|KNOWLEDGE|SKILLS|$))',
            r'(?i)LICENSES?\s+AND\s+CERTIFICATIONS?[^:]*:?\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|$))',
            r'(?i)((?:valid|current|active|must\s+(?:have|hold|possess))\s+[^.;]*(?:license|certification|certificate)[^.;]*[.;]?)',
        ]
        
        for pattern in cert_patterns:
            matches = re.findall(pattern, job_description, re.DOTALL)
            for match in matches:
                if match:
                    clean_match = self.clean_text(match)
                    if any(word in clean_match.lower() for word in ['license', 'certif', 'registration']):
                        cert_items.append(clean_match)
                        break
            if cert_items:
                break
        
        return cert_items[0] if cert_items else ""
    
    def extract_knowledge_skills_abilities(self, job_description: str) -> str:
        """Extract knowledge, skills, and abilities."""
        job_description = self.fix_encoding_issues(job_description)
        
        ksa_items = []
        
        # Look for KSA sections with various headers
        ksa_patterns = [
            r'(?i)(?:COMMUNICATION|LANGUAGE|MATHEMATICAL)\s+SKILLS:?\s*(.*?)(?=\n\s*(?:PHYSICAL|WORK\s+ENVIRONMENT|REASONING|$))',
            r'(?i)KNOWLEDGE,?\s+SKILLS,?\s+(?:AND\s+)?ABILITIES[^:]*:?\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|$))',
            r'(?i)(?:REQUIRED\s+|PREFERRED\s+)?SKILLS[^:]*:?\s*(.*?)(?=\n\s*(?:EDUCATION|EXPERIENCE|[A-Z\s]+:|$))',
            r'(?i)OTHER\s+SKILLS\s+AND\s+ABILITIES:?\s*(.*?)(?=\n\s*(?:PHYSICAL|WORK|$))',
            r'(?i)REASONING\s+ABILITY:?\s*(.*?)(?=\n\s*(?:CERTIFICATES|OTHER|PHYSICAL|$))',
            r'(?i)(?:COMPUTER|TECHNOLOGY)\s+SKILLS:?\s*(.*?)(?=\n\s*(?:OTHER|PHYSICAL|$))',
        ]
        
        for pattern in ksa_patterns:
            match = re.search(pattern, job_description, re.DOTALL)
            if match and match.group(1).strip():
                section_text = self.clean_text(match.group(1))
                
                # Split by newlines or semicolons
                items = re.split(r'[\n;]', section_text)
                
                for item in items:
                    item = item.strip()
                    if item and len(item) > 15:
                        ksa_items.append(item)
                
                if ksa_items:
                    break
        
        # Look for specific skill patterns if no section found
        if not ksa_items:
            skill_patterns = [
                r'(?i)((?:computer|communication|interpersonal|customer\s+service|analytical|problem\s+solving)\s+skills[^.;]*[.;]?)',
                r'(?i)(ability\s+to\s+[^.;]+[.;]?)',
                r'(?i)((?:strong|excellent|good)\s+[^.;]*skills[^.;]*[.;]?)',
                r'(?i)((?:knowledge|experience)\s+(?:of|with|in)\s+[^.;]+[.;]?)',
            ]
            
            for pattern in skill_patterns:
                matches = re.findall(pattern, job_description)
                for match in matches:
                    clean_match = self.clean_text(match)
                    if clean_match and len(clean_match) > 10:
                        ksa_items.append(clean_match)
                if len(ksa_items) >= 5:
                    break
        
        # Return up to 10 items, joined with newlines
        if ksa_items:
            return '\n'.join(ksa_items[:10])
        
        return ""
    
    def infer_position_summary(self, essential_functions: str, job_title: str) -> str:
        """Infer a position summary from essential functions."""
        if not essential_functions or not job_title:
            return ""
        
        # Take first 2-3 key functions
        functions = essential_functions.split('\n')
        key_functions = []
        
        for func in functions[:3]:
            func = func.strip()
            if func and len(func) > 20:
                # Convert to more natural language
                func = func.lower()
                if func.endswith('.'):
                    func = func[:-1]
                key_functions.append(func)
        
        if key_functions:
            if len(key_functions) >= 2:
                summary = f"*The {job_title} is responsible for {key_functions[0]} and {key_functions[1]}."
            else:
                summary = f"*The {job_title} is responsible for {key_functions[0]}."
            
            return summary
        
        return ""
    
    def process_single_job(self, row: Dict) -> Dict:
        """Process a single job row and extract structured data."""
        job_description = str(row.get('jobDescription-value', ''))
        job_title = str(row.get('job-details-job-title', ''))
        
        # Extract all sections
        position_summary = self.extract_position_summary(job_description)
        education = self.extract_education(job_description)
        work_experience = self.extract_work_experience(job_description)
        essential_functions = self.extract_essential_functions(job_description)
        licenses_certifications = self.extract_licenses_certifications(job_description)
        knowledge_skills_abilities = self.extract_knowledge_skills_abilities(job_description)
        
        # Infer position summary if not found
        if not position_summary and essential_functions:
            position_summary = self.infer_position_summary(essential_functions, job_title)
        
        result = {
            'Job Description Name': job_title,
            'Position Summary': position_summary,
            'Education': education,
            'Work Experience': work_experience,
            'Essential Functions': essential_functions,
            'Licenses and Certifications': licenses_certifications,
            'Knowledge, Skills and Abilities': knowledge_skills_abilities
        }
        
        return result
    
    def read_csv_with_diagnostics(self, input_file: str):
        """Read CSV with detailed diagnostics to identify issues."""
        print(f"Diagnosing CSV file: {input_file}")
        
        # First, try to count lines manually
        try:
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                print(f"Raw line count: {len(lines)}")
                print(f"First few lines:")
                for i, line in enumerate(lines[:5]):
                    print(f"  Line {i+1}: {repr(line[:100])}")
        except Exception as e:
            print(f"Error reading raw file: {e}")
        
        # Try different CSV reading approaches
        encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'latin1']
        df_input = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                # Try pandas first
                df_pandas = pd.read_csv(input_file, encoding=encoding, keep_default_na=False)
                print(f"Pandas with {encoding}: {len(df_pandas)} rows, {len(df_pandas.columns)} columns")
                print(f"Columns: {list(df_pandas.columns)}")
                
                # Try csv module
                with open(input_file, 'r', encoding=encoding, newline='') as csvfile:
                    dialect = csv.Sniffer().sniff(csvfile.read(1024))
                    csvfile.seek(0)
                    reader = csv.DictReader(csvfile, dialect=dialect)
                    csv_rows = list(reader)
                    print(f"CSV module with {encoding}: {len(csv_rows)} rows")
                
                if df_pandas is not None:
                    df_input = df_pandas
                    used_encoding = encoding
                    break
                    
            except Exception as e:
                print(f"Failed with {encoding}: {str(e)}")
                continue
        
        if df_input is None:
            raise ValueError("Could not read file with any encoding")
        
        print(f"Using {used_encoding} encoding, found {len(df_input)} rows")
        
        # Check for empty or problematic rows
        empty_title_count = 0
        empty_desc_count = 0
        both_empty_count = 0
        
        for index, row in df_input.iterrows():
            title = str(row.get('job-details-job-title', '')).strip()
            desc = str(row.get('jobDescription-value', '')).strip()
            
            if not title:
                empty_title_count += 1
            if not desc:
                empty_desc_count += 1
            if not title and not desc:
                both_empty_count += 1
                print(f"Row {index+1} has both empty title and description")
        
        print(f"Empty titles: {empty_title_count}")
        print(f"Empty descriptions: {empty_desc_count}")
        print(f"Both empty: {both_empty_count}")
        
        return df_input, used_encoding
    
    def transform_data(self, input_file: str, output_file: str) -> None:
        """Transform input CSV file to output format with enhanced diagnostics."""
        try:
            # Read with diagnostics
            df_input, used_encoding = self.read_csv_with_diagnostics(input_file)
            
            print(f"\nProcessing {len(df_input)} rows...")
            
            # Check for required columns
            required_columns = ['job-details-job-title', 'jobDescription-value']
            missing_columns = [col for col in required_columns if col not in df_input.columns]
            if missing_columns:
                print(f"Warning: Missing required columns: {missing_columns}")
            
            # Process each row with detailed tracking
            results = []
            skipped_rows = []
            processed_count = 0
            
            for index, row in df_input.iterrows():
                try:
                    job_title = str(row.get('job-details-job-title', '')).strip()
                    job_description = str(row.get('jobDescription-value', '')).strip()
                    
                    # Only skip if both are completely empty
                    if not job_title and not job_description:
                        print(f"Skipping row {index + 1}: Both title and description are empty")
                        skipped_rows.append(index + 1)
                        continue
                    
                    print(f"Processing row {index + 1}: '{job_title[:50]}{'...' if len(job_title) > 50 else ''}' (desc: {len(job_description)} chars)")
                    
                    result = self.process_single_job(row)
                    results.append(result)
                    processed_count += 1
                    
                except Exception as e:
                    print(f"Error processing row {index + 1}: {str(e)}")
                    # Still add a basic result to avoid losing the row
                    try:
                        basic_result = {
                            'Job Description Name': str(row.get('job-details-job-title', '')),
                            'Position Summary': '',
                            'Education': '',
                            'Work Experience': '',
                            'Essential Functions': '',
                            'Licenses and Certifications': '',
                            'Knowledge, Skills and Abilities': ''
                        }
                        results.append(basic_result)
                        processed_count += 1
                    except Exception as e2:
                        print(f"Could not create basic result for row {index + 1}: {str(e2)}")
                        skipped_rows.append(index + 1)
            
            print(f"\nProcessing complete:")
            print(f"Input rows: {len(df_input)}")
            print(f"Output rows: {len(results)}")
            print(f"Processed: {processed_count}")
            print(f"Skipped rows: {skipped_rows}")
            
            if len(results) != len(df_input):
                print(f"WARNING: Row count mismatch! Input: {len(df_input)}, Output: {len(results)}")
            
            # Create output DataFrame
            df_output = pd.DataFrame(results)
            
            # Ensure columns are in the expected order
            column_order = [
                'Job Description Name',
                'Position Summary',
                'Education',
                'Work Experience',
                'Essential Functions',
                'Licenses and Certifications',
                'Knowledge, Skills and Abilities'
            ]
            df_output = df_output[column_order]
            
            # Save to CSV
            print(f"Saving {len(df_output)} rows to: {output_file}")
            df_output.to_csv(output_file, index=False, encoding='utf-8-sig')
            print("File saved successfully")
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def preview_extraction(self, input_file: str, num_rows: int = 3) -> None:
        """Preview the extraction results with enhanced diagnostics."""
        try:
            df_input, used_encoding = self.read_csv_with_diagnostics(input_file)
            
            print(f"\nPreviewing first {num_rows} rows:")
            
            for index, row in df_input.head(num_rows).iterrows():
                print(f"\n{'='*80}")
                job_title = str(row.get('job-details-job-title', 'Unknown'))
                print(f"JOB {index + 1}: {job_title}")
                print(f"{'='*80}")
                
                # Show raw data
                job_desc = str(row.get('jobDescription-value', ''))
                print(f"Job Description Length: {len(job_desc)} characters")
                if len(job_desc) > 100:
                    print(f"Job Description Preview: {job_desc[:100]}...")
                
                try:
                    result = self.process_single_job(row)
                    
                    for field, value in result.items():
                        print(f"\n{field}:")
                        if value:
                            if len(value) > 300:
                                print(f"  {value[:300]}...")
                            else:
                                print(f"  {value}")
                        else:
                            print("  [No data extracted]")
                except Exception as e:
                    print(f"Error processing this job: {str(e)}")
                    import traceback
                    traceback.print_exc()
                        
        except Exception as e:
            print(f"Error previewing file: {str(e)}")
            import traceback
            traceback.print_exc()

def main():
    """Main function to run the job data extractor."""
    parser = argparse.ArgumentParser(description='Extract structured data from job postings (v6.1 - Enhanced Diagnostics)')
    parser.add_argument('input_file', nargs='?', help='Input CSV file path')
    parser.add_argument('-o', '--output', help='Output CSV file path', 
                       default='extracted_job_data_v6_1.csv')
    parser.add_argument('-p', '--preview', action='store_true', 
                       help='Preview extraction results without saving')
    parser.add_argument('-n', '--num-preview', type=int, default=3,
                       help='Number of jobs to preview (default: 3)')
    
    args = parser.parse_args()
    
    # If no input file provided, prompt for it
    input_file = args.input_file
    if not input_file:
        print("Job Data Extraction Tool v6.1 - Enhanced Diagnostics")
        print("=" * 50)
        input_file = input("Enter the path to your input CSV file: ").strip()
        if not input_file:
            print("Error: No input file specified.")
            sys.exit(1)
    
    # Strip quotes from file path
    input_file = input_file.strip('\'"')
    
    # If no output file specified and not in preview mode, prompt for it
    output_file = args.output
    if not args.preview and args.output == 'extracted_job_data_v6_1.csv':
        use_default = input(f"Use default output filename '{args.output}'? (y/n): ").strip().lower()
        if use_default not in ['y', 'yes', '']:
            output_file = input("Enter output CSV filename: ").strip()
            if not output_file:
                output_file = args.output
    
    # Ask about preview mode if not specified
    if not args.preview:
        preview_choice = input("Would you like to preview the extraction first? (y/n): ").strip().lower()
        if preview_choice in ['y', 'yes']:
            args.preview = True
    
    extractor = JobDataExtractor()
    
    if args.preview:
        print(f"\nPreviewing extraction results from '{input_file}'...")
        extractor.preview_extraction(input_file, args.num_preview)
        
        # Ask if user wants to proceed with full extraction
        proceed = input("\nProceed with full extraction? (y/n): ").strip().lower()
        if proceed in ['y', 'yes']:
            extractor.transform_data(input_file, output_file)
    else:
        extractor.transform_data(input_file, output_file)

if __name__ == "__main__":
    main()