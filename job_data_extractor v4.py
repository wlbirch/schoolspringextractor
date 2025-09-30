#============= job extractor data v4 ========
import pandas as pd
import re
import argparse
import sys
from typing import Dict, Optional, List

class JobDataExtractor:
    """
    Extracts structured data from job posting text and transforms it into standardized format.
    Version 4: Improved with character encoding fixes, bullet removal, and position summary inference.
    """
    
    def __init__(self):
        # Character replacements for common encoding issues
        self.char_replacements = {
            'â€™': "'",
            'â€"': "–",
            'â€"': "—",
            'â€œ': '"',
            'â€': '"',
            'Â': '',
            'â€¢': '•',
            '&amp;': '&',
            '&nbsp;': ' ',
            '\xa0': ' ',
            '\u2019': "'",
            '\u2018': "'",
            '\u201c': '"',
            '\u201d': '"',
            '\u2013': '–',
            '\u2014': '—',
        }
        
        # Define section patterns and keywords for extraction
        self.section_patterns = {
            'position_summary': [
                r'SUMMARY:\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|ESSENTIAL|EDUCATION|QUALIFICATIONS|$))',
                r'Position Summary:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Job Summary:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Overview:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'JOB GOAL:\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|$))'
            ],
            'education': [
                r'EDUCATION AND/OR EXPERIENCE:\s*(.*?)(?=\n\s*(?:CERTIFICATES|ESSENTIAL|[A-Z\s]+:|$))',
                r'QUALIFICATIONS:\s*Education[^:]*:\s*(.*?)(?=\n\s*(?:Experience|[A-Z\s]+:|$))',
                r'Education Requirements?:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'((?:Bachelor|Master|PhD|Doctorate|Associate|High School|Degree).*?(?:\.|;|$))',
                r'(Educational.*?(?:required|preferred|desired).*?(?:\.|;|$))',
                r'(Minimum education.*?(?:\.|;|$))'
            ],
            'work_experience': [
                r'EDUCATION AND/OR EXPERIENCE:\s*(.*?)(?=\n\s*(?:CERTIFICATES|ESSENTIAL|[A-Z\s]+:|$))',
                r'QUALIFICATIONS:\s*Experience[^:]*:\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|$))',
                r'Experience Requirements?:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'(\d+\s+(?:or more\s+)?years?\s+of\s+.*?experience[^.;]*[.;])',
                r'((?:Minimum|At least|Must have)\s+\d+\s+years?.*?experience[^.;]*[.;])',
                r'(Experience.*?(?:required|preferred|desired)[^.;]*[.;])',
                r'(Previous.*?experience[^.;]*[.;])'
            ],
            'essential_functions': [
                r'ESSENTIAL DUTIES AND RESPONSIBILITIES[^:]*:?\s*(.*?)(?=\n\s*(?:SUPERVISORY|QUALIFICATION|CERTIFICATES|COMMUNICATION|PHYSICAL|WORK ENVIRONMENT|$))',
                r'Essential Functions:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Key Responsibilities:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Primary Duties:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Overall Responsibilities:\s*(.*?)(?=(?:\n\s*[A-Z\s]+:|$))',
                r'SUPERVISORY RESPONSIBILITIES:\s*(.*?)(?=\n\s*(?:QUALIFICATION|CERTIFICATES|COMMUNICATION|$))',
                r'Major Responsibilities:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)'
            ],
            'licenses_certifications': [
                r'CERTIFICATES?, LICENSES?,? (?:AND\s+)?REGISTRATIONS?:\s*(.*?)(?=\n\s*(?:COMMUNICATION|MATHEMATICAL|REASONING|TECHNOLOGY|OTHER|PHYSICAL|LANGUAGE|$))',
                r'Licenses? and Certifications?:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Certification Requirements?:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'((?:Hold|Must have|Requires?).*?(?:valid|current).*?(?:certificate|certification|license)[^.;]*[.;])',
                r'(Certification.*?(?:required|preferred)[^.;]*[.;])',
                r'(.*?(?:licensed|certified).*?(?:required|preferred)[^.;]*[.;])'
            ],
            'knowledge_skills_abilities': [
                r'COMMUNICATION SKILLS:\s*(.*?)(?=\n\s*(?:PHYSICAL DEMANDS|WORK ENVIRONMENT|$))',
                r'LANGUAGE SKILLS:\s*(.*?)(?=\n\s*(?:MATHEMATICAL|REASONING|CERTIFICATES|PHYSICAL|$))',
                r'MATHEMATICAL SKILLS:\s*(.*?)(?=\n\s*(?:REASONING|CERTIFICATES|PHYSICAL|$))',
                r'REASONING ABILITY:\s*(.*?)(?=\n\s*(?:CERTIFICATES|OTHER|PHYSICAL|$))',
                r'Knowledge,? Skills,? and Abilities:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Required Skills:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'OTHER SKILLS AND ABILITIES:\s*(.*?)(?=\n\s*(?:PHYSICAL|WORK|$))',
                r'TECHNOLOGY:\s*(.*?)(?=\n\s*(?:OTHER|PHYSICAL|$))'
            ]
        }
    
    def fix_encoding_issues(self, text: str) -> str:
        """Fix common encoding issues in text."""
        if not text:
            return ""
        
        for bad_char, good_char in self.char_replacements.items():
            text = text.replace(bad_char, good_char)
        
        return text
    
    def remove_leading_bullets(self, text: str) -> str:
        """Remove leading bullets, dashes, asterisks, and numbers from text."""
        if not text:
            return ""
        
        # Process each line separately
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove leading bullets, dashes, asterisks, numbers with dots/parentheses
            line = re.sub(r'^\s*[-•*◦▪▫◆◇→⇒]\s*', '', line)
            line = re.sub(r'^\s*\d+[.)]\s*', '', line)
            line = re.sub(r'^\s*[a-zA-Z][.)]\s*', '', line)
            
            if line.strip():
                cleaned_lines.append(line.strip())
        
        return '\n'.join(cleaned_lines)
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Fix encoding issues first
        text = self.fix_encoding_issues(text)
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove leading bullets and formatting
        text = self.remove_leading_bullets(text)
        
        # Clean up common formatting issues
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'  +', ' ', text)
        
        # Remove trailing/leading punctuation artifacts
        text = re.sub(r'^[^\w]+|[^\w]+$', '', text)
        
        return text.strip()
    
    def extract_section(self, job_description: str, section_type: str) -> str:
        """Extract a specific section from job description text."""
        if not job_description or section_type not in self.section_patterns:
            return ""
        
        # Fix encoding issues in the entire job description first
        job_description = self.fix_encoding_issues(job_description)
        
        patterns = self.section_patterns[section_type]
        extracted_parts = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, job_description, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if match.groups():
                    extracted_text = match.group(1) if match.group(1) else match.group(0)
                    if extracted_text:
                        extracted_parts.append(extracted_text)
        
        # Combine and clean extracted parts, removing duplicates
        if extracted_parts:
            unique_parts = []
            for part in extracted_parts:
                cleaned_part = self.clean_text(part)
                if cleaned_part and cleaned_part not in unique_parts:
                    unique_parts.append(cleaned_part)
            
            combined = ' '.join(unique_parts)
            return self.clean_text(combined)
        
        return ""
    
    def extract_education_from_combined(self, job_description: str) -> str:
        """Extract education requirements from combined EDUCATION AND/OR EXPERIENCE sections."""
        education_lines = []
        
        # Look for combined section
        combined_pattern = r'EDUCATION AND/OR EXPERIENCE:\s*(.*?)(?=\n\s*(?:CERTIFICATES|ESSENTIAL|[A-Z\s]+:|$))'
        match = re.search(combined_pattern, job_description, re.IGNORECASE | re.DOTALL)
        
        if match:
            section_text = match.group(1)
            lines = section_text.split('\n')
            
            for line in lines:
                line = line.strip()
                # Look for education-related keywords
                if re.search(r'(?:Bachelor|Master|PhD|Doctorate|Associate|Degree|High School|Education|diploma)', line, re.IGNORECASE):
                    if not re.search(r'\d+\s+years?\s+of.*?experience', line, re.IGNORECASE):
                        education_lines.append(line)
        
        if education_lines:
            return self.clean_text('\n'.join(education_lines))
        
        return ""
    
    def extract_experience_from_combined(self, job_description: str) -> str:
        """Extract work experience from combined EDUCATION AND/OR EXPERIENCE sections."""
        experience_lines = []
        
        # Look for combined section
        combined_pattern = r'EDUCATION AND/OR EXPERIENCE:\s*(.*?)(?=\n\s*(?:CERTIFICATES|ESSENTIAL|[A-Z\s]+:|$))'
        match = re.search(combined_pattern, job_description, re.IGNORECASE | re.DOTALL)
        
        if match:
            section_text = match.group(1)
            lines = section_text.split('\n')
            
            for line in lines:
                line = line.strip()
                # Look for experience-related patterns
                if re.search(r'\d+\s+years?\s+of.*?experience', line, re.IGNORECASE):
                    experience_lines.append(line)
                elif re.search(r'experience.*?(?:required|preferred|desired)', line, re.IGNORECASE):
                    experience_lines.append(line)
        
        if experience_lines:
            return self.clean_text('\n'.join(experience_lines))
        
        return ""
    
    def infer_position_summary(self, essential_functions: str, job_title: str) -> str:
        """Infer a position summary from essential functions if no explicit summary exists."""
        if not essential_functions:
            return ""
        
        # Extract key responsibilities to create summary
        functions_list = essential_functions.split('.')[:3]  # Get first 3 sentences
        
        if functions_list:
            # Create an inferred summary
            key_responsibilities = []
            for func in functions_list:
                func = func.strip()
                if func and len(func) > 10:
                    # Clean up the function text
                    func = re.sub(r'^\d+[.)]\s*', '', func)
                    func = re.sub(r'^[-•*]\s*', '', func)
                    key_responsibilities.append(func.lower())
            
            if key_responsibilities:
                # Format as a summary
                if job_title:
                    summary = f"*The {job_title} is responsible for {', '.join(key_responsibilities[:2])}"
                else:
                    summary = f"*This position is responsible for {', '.join(key_responsibilities[:2])}"
                
                # Ensure proper sentence ending
                if not summary.endswith('.'):
                    summary += '.'
                
                return summary
        
        return ""
    
    def process_single_job(self, row: Dict) -> Dict:
        """Process a single job row and extract structured data."""
        job_description = str(row.get('jobDescription-value', ''))
        job_title = str(row.get('job-details-job-title', ''))
        
        # Extract position summary
        position_summary = self.extract_section(job_description, 'position_summary')
        
        # Extract essential functions first (needed for inference)
        essential_functions = self.extract_section(job_description, 'essential_functions')
        
        # If no position summary found, try to infer from essential functions
        if not position_summary and essential_functions:
            position_summary = self.infer_position_summary(essential_functions, job_title)
        
        # Extract education - try standard patterns first, then combined section
        education = self.extract_section(job_description, 'education')
        if not education:
            education = self.extract_education_from_combined(job_description)
        
        # Extract work experience - try standard patterns first, then combined section
        work_experience = self.extract_section(job_description, 'work_experience')
        if not work_experience:
            work_experience = self.extract_experience_from_combined(job_description)
        
        result = {
            'Job Description Name': job_title,
            'Position Summary': position_summary,
            'Education': education,
            'Work Experience': work_experience,
            'Essential Functions': essential_functions,
            'Licenses and Certifications': self.extract_section(job_description, 'licenses_certifications'),
            'Knowledge, Skills and Abilities': self.extract_section(job_description, 'knowledge_skills_abilities')
        }
        
        return result
    
    def transform_data(self, input_file: str, output_file: str) -> None:
        """Transform input CSV file to output format."""
        try:
            # Read input CSV with proper encoding handling
            print(f"Reading input file: {input_file}")
            
            # Try different encodings
            encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'latin1']
            df_input = None
            
            for encoding in encodings:
                try:
                    df_input = pd.read_csv(input_file, encoding=encoding)
                    print(f"Successfully read file with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df_input is None:
                raise ValueError("Could not read file with any common encoding")
            
            print(f"Found {len(df_input)} rows in input file")
            
            # Process each row
            results = []
            for index, row in df_input.iterrows():
                job_title = row.get('job-details-job-title', 'Unknown')
                print(f"Processing job {index + 1}: {job_title}")
                result = self.process_single_job(row)
                results.append(result)
            
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
            
            # Save to CSV with proper encoding
            print(f"Saving results to: {output_file}")
            df_output.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"Successfully processed {len(results)} jobs")
            
        except FileNotFoundError:
            print(f"Error: Input file '{input_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            sys.exit(1)
    
    def preview_extraction(self, input_file: str, num_rows: int = 3) -> None:
        """Preview the extraction results for debugging."""
        try:
            # Try different encodings
            encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'latin1']
            df_input = None
            
            for encoding in encodings:
                try:
                    df_input = pd.read_csv(input_file, encoding=encoding)
                    print(f"Reading file with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df_input is None:
                raise ValueError("Could not read file with any common encoding")
            
            for index, row in df_input.head(num_rows).iterrows():
                print(f"\n{'='*80}")
                print(f"JOB {index + 1}: {row.get('job-details-job-title', 'Unknown')}")
                print(f"{'='*80}")
                
                result = self.process_single_job(row)
                
                for field, value in result.items():
                    print(f"\n{field}:")
                    if value:
                        # Show more of the content for preview
                        preview_text = value[:300] + '...' if len(value) > 300 else value
                        print(f"  {preview_text}")
                    else:
                        print("  [No data extracted]")
                        
        except Exception as e:
            print(f"Error previewing file: {str(e)}")

def main():
    """Main function to run the job data extractor."""
    parser = argparse.ArgumentParser(description='Extract structured data from job postings (v4)')
    parser.add_argument('input_file', nargs='?', help='Input CSV file path')
    parser.add_argument('-o', '--output', help='Output CSV file path', 
                       default='extracted_job_data.csv')
    parser.add_argument('-p', '--preview', action='store_true', 
                       help='Preview extraction results without saving')
    parser.add_argument('-n', '--num-preview', type=int, default=3,
                       help='Number of jobs to preview (default: 3)')
    
    args = parser.parse_args()
    
    # If no input file provided, prompt for it
    input_file = args.input_file
    if not input_file:
        print("Job Data Extraction Tool v4")
        print("=" * 40)
        input_file = input("Enter the path to your input CSV file: ").strip()
        if not input_file:
            print("Error: No input file specified.")
            sys.exit(1)
    
    # Strip quotes from file path (common when copying from Windows Explorer)
    input_file = input_file.strip('\'"')
    
    # If no output file specified and not in preview mode, prompt for it
    output_file = args.output
    if not args.preview and args.output == 'extracted_job_data.csv':
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