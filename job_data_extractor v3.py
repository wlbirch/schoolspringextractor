import pandas as pd
import re
import argparse
import sys
from typing import Dict, Optional

class JobDataExtractor:
    """
    Extracts structured data from job posting text and transforms it into standardized format.
    """
    
    def __init__(self):
        # Define section patterns and keywords for extraction
        self.section_patterns = {
            'position_summary': [
                r'SUMMARY:\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|ESSENTIAL|EDUCATION|QUALIFICATIONS))',
                r'Position Summary:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Job Summary:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Overview:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)'
            ],
            'education': [
                # Separate education from experience - look for degree/education requirements only
                r'((?:Bachelor|Master|PhD|Doctorate|Associate|Degree).*?(?:\.|$))',
                r'(Educational.*?(?:required|preferred|desired).*?(?:\.|$))',
                r'(Minimum education.*?(?:\.|$))'
            ],
            'work_experience': [
                # Focus on experience requirements specifically
                r'(\d+\s+(?:or more\s+)?years?\s+of\s+.*?experience[^.]*\.)',
                r'((?:Minimum|At least|Must have)\s+\d+\s+years?.*?experience[^.]*\.)',
                r'(Experience in.*?(?:required|preferred|desired)[^.]*\.)',
                r'(.*?years?\s+of\s+(?:teaching|administrative|supervisory|management|professional).*?experience[^.]*\.)',
                r'(Previous.*?experience[^.]*\.)'
            ],
            'essential_functions': [
                r'ESSENTIAL DUTIES AND RESPONSIBILITIES[^:]*:?\s*(.*?)(?=\n\s*(?:SUPERVISORY|QUALIFICATION|CERTIFICATES|COMMUNICATION|PHYSICAL|WORK ENVIRONMENT))',
                r'Essential Functions:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Key Responsibilities:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Primary Duties:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Overall Responsibilities:\s*(.*?)(?=(?:\n\s*[A-Z\s]+:|$))',
                r'SUPERVISORY RESPONSIBILITIES:\s*(.*?)(?=\n\s*(?:QUALIFICATION|CERTIFICATES|COMMUNICATION))'
            ],
            'licenses_certifications': [
                r'CERTIFICATES?, LICENSES, REGISTRATIONS:\s*(.*?)(?=\n\s*(?:COMMUNICATION|MATHEMATICAL|REASONING|TECHNOLOGY|OTHER|PHYSICAL))',
                r'Licenses? and Certifications?:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Certification Requirements?:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'(Hold a valid.*?(?:certificate|certification|license)[^.]*\.)',
                r'(Certification for.*?(?:\.|$))',
                r'(.*?(?:licensed|certified).*?(?:required|preferred)[^.]*\.)'
            ],
            'knowledge_skills_abilities': [
                r'COMMUNICATION SKILLS:\s*(.*?)(?=\n\s*(?:PHYSICAL DEMANDS|WORK ENVIRONMENT|$))',
                r'Knowledge,? Skills,? and Abilities:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'Required Skills:\s*(.*?)(?=\n\s*[A-Z\s]+:|$)',
                r'OTHER SKILLS AND ABILITIES:\s*(.*?)(?=\n\s*(?:PHYSICAL|WORK|$))',
                r'TECHNOLOGY:\s*(.*?)(?=\n\s*(?:OTHER|PHYSICAL|$))'
            ]
        }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove leading/trailing punctuation artifacts
        text = re.sub(r'^[^\w]+|[^\w]+$', '', text)
        # Clean up common formatting issues
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'  +', ' ', text)
        
        return text.strip()
    
    def extract_section(self, job_description: str, section_type: str) -> str:
        """Extract a specific section from job description text."""
        if not job_description or section_type not in self.section_patterns:
            return ""
        
        patterns = self.section_patterns[section_type]
        extracted_parts = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, job_description, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if match.group(1):
                    extracted_parts.append(match.group(1))
        
        # Combine and clean extracted parts, removing duplicates
        if extracted_parts:
            # Remove duplicates while preserving order
            unique_parts = []
            for part in extracted_parts:
                cleaned_part = self.clean_text(part)
                if cleaned_part and cleaned_part not in unique_parts:
                    unique_parts.append(cleaned_part)
            
            combined = '\n'.join(unique_parts)
            return self.clean_text(combined)
        
        return ""
    
    def extract_position_summary(self, job_description: str) -> str:
        """Extract position summary with enhanced logic."""
        # First try standard patterns
        summary = self.extract_section(job_description, 'position_summary')
        
        # If no summary found, try to extract responsibility statements
        if not summary:
            # Look for "The [job title]'s responsibility..." patterns
            responsibility_patterns = [
                r"(The\s+[\w\s]+(?:Clinician|Teacher|Principal|Manager|Director|Analyst)\'s\s+responsibility.*?communications\.)",
                r"(The\s+[\w\s]+(?:position|role)\s+is\s+responsible.*?\.)",
                r"(This\s+position.*?responsible.*?\.)"
            ]
            
            for pattern in responsibility_patterns:
                match = re.search(pattern, job_description, re.IGNORECASE | re.DOTALL)
                if match:
                    summary = match.group(1)
                    break
        
        return self.clean_text(summary)
    
    def extract_work_experience(self, job_description: str) -> str:
        """Extract work experience with special handling for combined sections."""
        # First try standard experience patterns
        experience = self.extract_section(job_description, 'work_experience')
        
        # If not found, look in combined EDUCATION AND/OR EXPERIENCE sections
        if not experience:
            education_experience_pattern = r'EDUCATION AND/OR EXPERIENCE:\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|ESSENTIAL|$))'
            match = re.search(education_experience_pattern, job_description, re.IGNORECASE | re.DOTALL)
            
            if match:
                section_text = match.group(1)
                # Extract only experience-related lines
                experience_lines = []
                for line in section_text.split('\n'):
                    line = line.strip()
                    if re.search(r'\d+\s+years?\s+of.*?experience', line, re.IGNORECASE):
                        experience_lines.append(line)
                    elif re.search(r'experience.*?(?:required|preferred|desired)', line, re.IGNORECASE):
                        experience_lines.append(line)
                
                if experience_lines:
                    experience = '\n'.join(experience_lines)
        
        return self.clean_text(experience)
    
    def extract_essential_functions(self, job_description: str) -> str:
        """Extract essential functions with enhanced pattern matching."""
        # Try standard patterns first
        functions = self.extract_section(job_description, 'essential_functions')
        
        # If not found, try to find numbered lists that look like responsibilities
        if not functions:
            # Look for "Overall Responsibilities:" specifically
            overall_pattern = r'Overall Responsibilities:\s*(.*?)(?=\n\s*(?:[A-Z\s]+:|$))'
            match = re.search(overall_pattern, job_description, re.IGNORECASE | re.DOTALL)
            if match:
                functions = "Overall Responsibilities:\n" + match.group(1)
        
        return self.clean_text(functions)
    
    def process_single_job(self, row: Dict) -> Dict:
        """Process a single job row and extract structured data."""
        job_description = str(row.get('jobDescription-value', ''))
        
        result = {
            'Job Code': row.get('jobID-value', ''),
            'Job Description Name': row.get('job-details-job-title', ''),
            'Position Summary': self.extract_position_summary(job_description),
            'Education': self.extract_section(job_description, 'education'),
            'Work Experience': self.extract_work_experience(job_description),
            'Essential Functions': self.extract_essential_functions(job_description),
            'Licenses and Certifications': self.extract_section(job_description, 'licenses_certifications'),
            'Knowledge, Skills and Abilities': self.extract_section(job_description, 'knowledge_skills_abilities')
        }
        
        return result
    
    def transform_data(self, input_file: str, output_file: str) -> None:
        """Transform input CSV file to output format."""
        try:
            # Read input CSV
            print(f"Reading input file: {input_file}")
            df_input = pd.read_csv(input_file)
            print(f"Found {len(df_input)} rows in input file")
            
            # Process each row
            results = []
            for index, row in df_input.iterrows():
                print(f"Processing job {index + 1}: {row.get('job-details-job-title', 'Unknown')}")
                result = self.process_single_job(row)
                results.append(result)
            
            # Create output DataFrame
            df_output = pd.DataFrame(results)
            
            # Reorder columns to match expected format
            column_order = [
                'Job Code', 
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
            print(f"Saving results to: {output_file}")
            df_output.to_csv(output_file, index=False)
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
            df_input = pd.read_csv(input_file)
            
            for index, row in df_input.head(num_rows).iterrows():
                print(f"\n{'='*80}")
                print(f"JOB {index + 1}: {row.get('job-details-job-title', 'Unknown')}")
                print(f"{'='*80}")
                
                result = self.process_single_job(row)
                
                for field, value in result.items():
                    if field not in ['Job Code', 'Job Description Name']:
                        print(f"\n{field}:")
                        print(f"  {value[:200]}{'...' if len(value) > 200 else ''}")
                        
        except Exception as e:
            print(f"Error previewing file: {str(e)}")

def main():
    """Main function to run the job data extractor."""
    parser = argparse.ArgumentParser(description='Extract structured data from job postings')
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
        print("Job Data Extraction Tool")
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
        
        if not args.preview:  # If preview was chosen interactively
            proceed = input("\nProceed with full extraction? (y/n): ").strip().lower()
            if proceed in ['y', 'yes']:
                extractor.transform_data(input_file, output_file)
    else:
        extractor.transform_data(input_file, output_file)

if __name__ == "__main__":
    main()