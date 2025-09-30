import pandas as pd
import re
import argparse
import sys
from typing import Dict, Optional, List

class JobDataExtractor:
    """
    Extracts structured data from job posting text and transforms it into standardized format.
    Version 5: Major improvements to section extraction and text parsing.
    """
    
    def __init__(self):
        # Comprehensive character replacements for encoding issues
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
            'Ã¢â‚¬â„¢': "'",
            'â€‹': '',
            'Ã¢â‚¬': '"',
            'Ã¢â‚¬Â': '',
        }
    
    def fix_encoding_issues(self, text: str) -> str:
        """Fix common encoding issues in text."""
        if not text:
            return ""
        
        # Apply replacements
        for bad_char, good_char in self.char_replacements.items():
            text = text.replace(bad_char, good_char)
        
        # Additional cleanup for common patterns
        text = re.sub(r'Ã¢â‚¬â„¢', "'", text)
        text = re.sub(r'â€™', "'", text)
        text = re.sub(r'â€œ', '"', text)
        text = re.sub(r'â€', '"', text)
        
        return text
    
    def remove_leading_bullets(self, text: str) -> str:
        """Remove leading bullets, dashes, asterisks, and numbers from text."""
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove leading bullets and numbering
            line = re.sub(r'^\s*[-•*◦▪▫◆◇→⇒·]\s*', '', line)
            line = re.sub(r'^\s*\d+[.)]\s*', '', line)
            line = re.sub(r'^\s*[a-zA-Z][.)]\s*', '', line)
            line = re.sub(r'^\s*\([a-zA-Z0-9]+\)\s*', '', line)
            
            if line.strip():
                cleaned_lines.append(line.strip())
        
        return '\n'.join(cleaned_lines)
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Fix encoding issues first
        text = self.fix_encoding_issues(text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # Remove leading bullets
        text = self.remove_leading_bullets(text)
        
        # Clean up spacing
        text = re.sub(r'  +', ' ', text)
        text = text.strip()
        
        return text
    
    def extract_position_summary(self, job_description: str) -> str:
        """Extract position summary with multiple strategies."""
        job_description = self.fix_encoding_issues(job_description)
        
        # Strategy 1: Look for explicit summary sections
        summary_patterns = [
            r'(?:Position\s+)?Summary:?\s*(.*?)(?=\n\s*(?:Education|Experience|Qualifications|Essential|Responsibilities|$))',
            r'JOB\s+GOAL:?\s*(.*?)(?=\n\s*(?:Education|Experience|Qualifications|Essential|$))',
            r'Overview:?\s*(.*?)(?=\n\s*(?:Education|Experience|Qualifications|Essential|$))',
            r'Job\s+Summary:?\s*(.*?)(?=\n\s*(?:Education|Experience|Qualifications|Essential|$))',
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, job_description, re.IGNORECASE | re.DOTALL)
            if match and match.group(1).strip():
                summary = self.clean_text(match.group(1))
                if len(summary) > 20:  # Ensure it's substantial
                    return summary
        
        # Strategy 2: Look for description at the beginning
        lines = job_description.split('\n')
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            if len(line) > 50 and not re.match(r'^[A-Z\s]+:', line):
                # Check if it looks like a summary sentence
                if 'responsible for' in line.lower() or 'position' in line.lower() or 'role' in line.lower():
                    return self.clean_text(line)
        
        return ""
    
    def extract_education(self, job_description: str) -> str:
        """Extract education requirements with improved parsing."""
        job_description = self.fix_encoding_issues(job_description)
        
        education_items = []
        
        # Look for education section headers
        education_section_patterns = [
            r'Education(?:\s+Requirements)?:?\s*(.*?)(?=\n\s*(?:Experience|Licenses|Knowledge|Skills|Essential|$))',
            r'EDUCATION\s+AND(?:/OR)?\s+EXPERIENCE:?\s*(.*?)(?=\n\s*(?:CERTIFICATES|ESSENTIAL|SUPERVISORY|QUALIFICATIONS|$))',
            r'Qualifications:?\s*Education:?\s*(.*?)(?=\n\s*(?:Experience|$))',
        ]
        
        for pattern in education_section_patterns:
            match = re.search(pattern, job_description, re.IGNORECASE | re.DOTALL)
            if match:
                section_text = match.group(1)
                
                # Extract education-specific lines
                lines = section_text.split('\n')
                for line in lines:
                    line = line.strip()
                    # Check for education keywords
                    if re.search(r'(?:Bachelor|Master|PhD|Doctorate|Associate|Degree|Diploma|GED|High School)', line, re.IGNORECASE):
                        # Make sure it's not primarily about experience
                        if not re.search(r'\d+\s+(?:years?|months?)\s+(?:of\s+)?(?:experience|working)', line, re.IGNORECASE):
                            education_items.append(self.clean_text(line))
                            break  # Usually only need the first education requirement
        
        # Also look for inline education requirements
        if not education_items:
            inline_patterns = [
                r'((?:Bachelor|Master|PhD|Associate)(?:\'s|s)?\s+degree[^.;]*[.;])',
                r'(High\s+School\s+(?:Diploma|diploma)\s+or\s+GED[^.;]*[.;]?)',
                r'((?:Minimum\s+)?(?:Education|Educational)[^:]*:\s*[^.;]+[.;])',
            ]
            
            for pattern in inline_patterns:
                matches = re.findall(pattern, job_description, re.IGNORECASE)
                for match in matches:
                    clean_match = self.clean_text(match)
                    if clean_match and not any(exp in clean_match.lower() for exp in ['years of experience', 'months of experience']):
                        education_items.append(clean_match)
                        break
                if education_items:
                    break
        
        if education_items:
            # Join and clean, removing duplicates
            result = '; '.join(list(dict.fromkeys(education_items)))
            return self.clean_text(result)
        
        return ""
    
    def extract_work_experience(self, job_description: str) -> str:
        """Extract work experience with improved parsing."""
        job_description = self.fix_encoding_issues(job_description)
        
        experience_items = []
        
        # Look for experience in various sections
        experience_patterns = [
            r'Experience(?:\s+Requirements)?:?\s*(.*?)(?=\n\s*(?:Education|Licenses|Knowledge|Skills|Essential|$))',
            r'Work\s+Experience:?\s*(.*?)(?=\n\s*(?:Education|Licenses|Knowledge|Skills|Essential|$))',
            r'(\d+\s+(?:or\s+more\s+)?(?:years?|months?)\s+(?:of\s+)?[^.;]*?experience[^.;]*[.;])',
            r'((?:Minimum|At\s+least|Must\s+have)\s+\d+\s+(?:years?|months?)[^.;]*?experience[^.;]*[.;])',
        ]
        
        for pattern in experience_patterns:
            matches = re.findall(pattern, job_description, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if match:
                    # Clean and check if it's actually about experience
                    clean_match = self.clean_text(match)
                    if re.search(r'\d+\s+(?:years?|months?)', clean_match, re.IGNORECASE):
                        # Make sure it's not about education
                        if not any(edu in clean_match.lower() for edu in ['bachelor', 'master', 'degree', 'diploma']):
                            experience_items.append(clean_match)
                            break
            if experience_items:
                break
        
        # Look in combined Education/Experience sections
        if not experience_items:
            combined_pattern = r'EDUCATION\s+AND(?:/OR)?\s+EXPERIENCE:?\s*(.*?)(?=\n\s*(?:CERTIFICATES|ESSENTIAL|SUPERVISORY|$))'
            match = re.search(combined_pattern, job_description, re.IGNORECASE | re.DOTALL)
            if match:
                section_text = match.group(1)
                lines = section_text.split('.')
                for line in lines:
                    if re.search(r'\d+\s+(?:years?|months?)\s+(?:of\s+)?.*?experience', line, re.IGNORECASE):
                        experience_items.append(self.clean_text(line))
                        break
        
        if experience_items:
            return self.clean_text(experience_items[0])
        
        return ""
    
    def extract_essential_functions(self, job_description: str) -> str:
        """Extract essential functions/duties with comprehensive pattern matching."""
        job_description = self.fix_encoding_issues(job_description)
        
        functions = []
        
        # Look for various section headers
        function_patterns = [
            r'Essential\s+(?:Duties\s+and\s+)?(?:Functions|Responsibilities)[^:]*:?\s*(.*?)(?=\n\s*(?:SUPERVISORY|QUALIFICATIONS?|CERTIFICATES?|COMMUNICATION|PHYSICAL|WORK\s+ENVIRONMENT|Education|Experience|$))',
            r'(?:Key\s+)?Responsibilities[^:]*:?\s*(.*?)(?=\n\s*(?:Qualifications?|Requirements?|Education|Experience|$))',
            r'Primary\s+Duties[^:]*:?\s*(.*?)(?=\n\s*(?:Qualifications?|Requirements?|Education|$))',
            r'Major\s+Responsibilities[^:]*:?\s*(.*?)(?=\n\s*(?:Qualifications?|Requirements?|Education|$))',
            r'Job\s+Duties[^:]*:?\s*(.*?)(?=\n\s*(?:Qualifications?|Requirements?|Education|$))',
            r'SUPERVISORY\s+RESPONSIBILITIES:?\s*(.*?)(?=\n\s*(?:QUALIFICATIONS?|CERTIFICATES?|$))',
        ]
        
        for pattern in function_patterns:
            match = re.search(pattern, job_description, re.IGNORECASE | re.DOTALL)
            if match and match.group(1).strip():
                section_text = match.group(1)
                
                # Clean up the section text
                section_text = self.clean_text(section_text)
                
                # Split by common delimiters (newlines, semicolons)
                items = re.split(r'[\n;]', section_text)
                
                for item in items:
                    item = self.remove_leading_bullets(item).strip()
                    # Only add substantial items (more than a few words)
                    if item and len(item) > 20:
                        functions.append(item)
                
                if functions:
                    break
        
        # If no functions found, look for bulleted lists in the description
        if not functions:
            # Look for patterns that indicate responsibilities
            lines = job_description.split('\n')
            collecting = False
            
            for line in lines:
                line_stripped = line.strip()
                
                # Start collecting if we see a responsibilities header
                if re.search(r'(?:responsibilities|duties|functions)', line_stripped, re.IGNORECASE):
                    collecting = True
                    continue
                
                # Stop collecting at next section
                if collecting and re.match(r'^[A-Z\s]+:', line_stripped):
                    break
                
                # Collect lines that look like responsibilities
                if collecting or re.match(r'^[-•*]\s*', line_stripped):
                    cleaned = self.remove_leading_bullets(line_stripped).strip()
                    if cleaned and len(cleaned) > 20:
                        functions.append(cleaned)
        
        if functions:
            return '\n'.join(functions[:15])  # Limit to first 15 items
        
        return ""
    
    def extract_licenses_certifications(self, job_description: str) -> str:
        """Extract licenses and certifications."""
        job_description = self.fix_encoding_issues(job_description)
        
        cert_items = []
        
        # Look for certification sections
        cert_patterns = [
            r'(?:CERTIFICATES?|LICENSES?|REGISTRATIONS?)[^:]*:?\s*(.*?)(?=\n\s*(?:COMMUNICATION|MATHEMATICAL|REASONING|TECHNOLOGY|OTHER|PHYSICAL|LANGUAGE|Knowledge|$))',
            r'Licenses?\s+and\s+Certifications?[^:]*:?\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|$))',
            r'((?:Valid|Current|Active)\s+[^.;]*(?:license|certification|certificate)[^.;]*[.;])',
            r'(Must\s+(?:have|hold|possess)\s+[^.;]*(?:license|certification|certificate)[^.;]*[.;])',
        ]
        
        for pattern in cert_patterns:
            matches = re.findall(pattern, job_description, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if match:
                    clean_match = self.clean_text(match)
                    if 'license' in clean_match.lower() or 'certif' in clean_match.lower():
                        cert_items.append(clean_match)
                        break
            if cert_items:
                break
        
        if cert_items:
            return self.clean_text(cert_items[0])
        
        return ""
    
    def extract_knowledge_skills_abilities(self, job_description: str) -> str:
        """Extract knowledge, skills, and abilities."""
        job_description = self.fix_encoding_issues(job_description)
        
        ksa_items = []
        
        # Look for KSA sections
        ksa_patterns = [
            r'(?:COMMUNICATION|LANGUAGE|MATHEMATICAL)\s+SKILLS:?\s*(.*?)(?=\n\s*(?:PHYSICAL|WORK\s+ENVIRONMENT|$))',
            r'Knowledge,?\s+Skills,?\s+(?:and\s+)?Abilities[^:]*:?\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|$))',
            r'Required\s+Skills[^:]*:?\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|$))',
            r'OTHER\s+SKILLS\s+AND\s+ABILITIES:?\s*(.*?)(?=\n\s*(?:PHYSICAL|WORK|$))',
            r'REASONING\s+ABILITY:?\s*(.*?)(?=\n\s*(?:CERTIFICATES|OTHER|PHYSICAL|$))',
            r'Skills(?:\s+Requirements)?:?\s*(.*?)(?=\n\s*(?:Education|Experience|$))',
        ]
        
        for pattern in ksa_patterns:
            match = re.search(pattern, job_description, re.IGNORECASE | re.DOTALL)
            if match and match.group(1).strip():
                section_text = self.clean_text(match.group(1))
                
                # Split by newlines or semicolons
                items = re.split(r'[\n;]', section_text)
                
                for item in items:
                    item = self.remove_leading_bullets(item).strip()
                    if item and len(item) > 15:
                        ksa_items.append(item)
                
                if ksa_items:
                    break
        
        # Look for specific skill patterns if no section found
        if not ksa_items:
            skill_patterns = [
                r'((?:Computer|Communication|Interpersonal|Customer\s+service)\s+skills[^.;]*[.;])',
                r'(Ability\s+to\s+[^.;]+[.;])',
                r'((?:Good|Strong|Excellent)\s+[^.;]*skills[^.;]*[.;])',
            ]
            
            for pattern in skill_patterns:
                matches = re.findall(pattern, job_description, re.IGNORECASE)
                for match in matches:
                    clean_match = self.clean_text(match)
                    if clean_match:
                        ksa_items.append(clean_match)
                if len(ksa_items) >= 3:
                    break
        
        if ksa_items:
            return '\n'.join(ksa_items[:10])  # Limit to first 10 items
        
        return ""
    
    def infer_position_summary(self, essential_functions: str, job_title: str) -> str:
        """Infer a position summary from essential functions if no explicit summary exists."""
        if not essential_functions:
            return ""
        
        # Take first 2-3 key functions to create summary
        functions = essential_functions.split('\n')
        key_functions = []
        
        for func in functions[:3]:
            func = func.strip()
            if func and len(func) > 20:
                # Convert to lowercase and remove ending punctuation for flow
                func = func.lower().rstrip('.')
                key_functions.append(func)
        
        if key_functions:
            # Create summary based on job title and functions
            if len(key_functions) >= 2:
                summary = f"*The {job_title} is responsible for {key_functions[0]} and {key_functions[1]}."
            elif len(key_functions) == 1:
                summary = f"*The {job_title} is responsible for {key_functions[0]}."
            else:
                summary = f"*This position is responsible for various duties as outlined in the essential functions."
            
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
    
    def transform_data(self, input_file: str, output_file: str) -> None:
        """Transform input CSV file to output format."""
        try:
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
                        # Show more content in preview
                        if len(value) > 300:
                            print(f"  {value[:300]}...")
                        else:
                            print(f"  {value}")
                    else:
                        print("  [No data extracted]")
                        
        except Exception as e:
            print(f"Error previewing file: {str(e)}")

def main():
    """Main function to run the job data extractor."""
    parser = argparse.ArgumentParser(description='Extract structured data from job postings (v5)')
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
        print("Job Data Extraction Tool v5")
        print("=" * 40)
        input_file = input("Enter the path to your input CSV file: ").strip()
        if not input_file:
            print("Error: No input file specified.")
            sys.exit(1)
    
    # Strip quotes from file path
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