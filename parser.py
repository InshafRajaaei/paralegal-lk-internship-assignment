"""Judge extraction logic using regex patterns and positional heuristics."""

import re
from typing import List, Set


def extract_bench_judges(text: str) -> List[str]:
    """
    Extract judges from the bench section using positional heuristics.
    
    Looks for keywords like "Before:", "Present:", "Coram", or just "Before judge_name"
    and judges listed after "SUPREME COURT", "HIGH COURT", "COURT OF APPEAL".
    
    Args:
        text: Full text content of the court decision
        
    Returns:
        List of judge names on the bench
    """
    bench_judges = []
    lines = text.split('\n')
    
    # Strategy 1: Look for explicit keywords "Before:", "Present:", "Coram" (with colon)
    for i, line in enumerate(lines):
        if re.search(r'(?:Before|Present|Coram)\s*:', line, re.IGNORECASE):
            match = re.search(r'(?:Before|Present|Coram)\s*:\s*(.*)', line, re.IGNORECASE)
            if match and match.group(1).strip():
                judges = _parse_judge_line(match.group(1).strip())
                bench_judges.extend(judges)
            # Check next lines for additional judges
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                # Continue until we hit an empty line or section markers
                if not next_line or re.match(r'^[\d]*\s*(?:[A-Z][a-z]+\s+)?(?:Counsel|Counse|S\.C\.|Vs\.|Pleadings)', next_line, re.IGNORECASE):
                    break
                # Match judge titles more flexibly: J (with or without period), J ., CJ, PC, etc.
                if re.search(r'(?:\bJ[\.\s]?|\bCJ\b|Chief Justice|PC\b)', next_line):
                    judges = _parse_judge_line(next_line)
                    bench_judges.extend(judges)
                j += 1
    
    # Strategy 2: If nothing found, look for "Before" followed directly by judge name (no colon)
    # Pattern: "Before JUDGE_NAME, TITLE"
    if not bench_judges:
        for i, line in enumerate(lines):
            match = re.match(r'^\s*Before\s+([A-Z].*)', line, re.IGNORECASE)
            if match:
                judge_text = match.group(1).strip()
                judges = _parse_judge_line(judge_text)
                bench_judges.extend(judges)
                
                # Collect additional judges from following lines
                j = i + 1
                while j < len(lines) and j < i + 10:  # Look ahead up to 10 lines
                    next_line = lines[j].strip()
                    if not next_line:
                        break
                    # Stop if we hit section markers like "S.C.", "Vs.", "Counsel:", etc.
                    if re.match(r'^(?:S\.C\.|Vs\.|Counsel|Counse|and\s|instructed)', next_line, re.IGNORECASE):
                        break
                    # Check if it's a judge line (has a judgment title)
                    if re.search(r'(?:J\.|CJ|Chief Justice|PC)', next_line):
                        judges = _parse_judge_line(next_line)
                        bench_judges.extend(judges)
                    j += 1
                break
    
    # Strategy 3: Look for judges after SUPREME COURT/HIGH COURT headers
    if not bench_judges:
        for i, line in enumerate(lines):
            if re.search(r'(?:SUPREME COURT|HIGH COURT|COURT OF APPEAL)\s*\.?', line, re.IGNORECASE):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Check if it looks like judge names
                    if next_line and re.search(r'[A-Z].*?(?:J\.|CJ)', next_line):
                        judges = _parse_judge_line(next_line)
                        bench_judges.extend(judges)
                        break
    
    # Strategy 4 (OCR fallback): Look for judge names followed by "Chief Justice" or "Judge of the Supreme Court"
    # This handles OCR output where judge info is formatted as:
    # "G.P.S. de Silva," → "Chief Justice"
    # Also handles: "A.R.B. Amarasinghe, æ" or "A.R.B. Amarasinghe, '" → "Judge of the Supreme Court"
    if not bench_judges:
        for i, line in enumerate(lines):
            current = line.strip()
            # Clean up OCR artifacts (common patterns)
            current = re.sub(r'^[\s\.\:,]+', '', current)  # Remove leading dots, colons, spaces
            current = re.sub(r'^\s*[a-z]{1,3}\s+', '', current, flags=re.IGNORECASE)  # Remove small letter prefixes like "mo ", "ms "
            current = current.strip()
            
            # Look for next line with judge title
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Clean next_line too
                next_line_clean = re.sub(r'^[\s\.\:,]+', '', next_line)
                next_line_clean = re.sub(r'^\s*[a-z]{1,3}\s+', '', next_line_clean, flags=re.IGNORECASE).strip()
                
                # Check if next line has judge title
                if re.match(r'^(?:Chief Justice|Judge of)', next_line_clean, re.IGNORECASE):
                    # Extract name: remove trailing non-alphanumeric and punctuation
                    name = re.sub(r'[^\w\s\.\-]', '', current)  # Remove special chars
                    name = name.strip()
                    title = next_line_clean.split('.')[0].split(',')[0].strip()
                    # Validate : name should have uppercase letters and be reasonable length
                    if (len(name) > 2 and len(name) < 50 and len(title) > 2 and 
                        re.search(r'[A-Z]', name)):  # Must have uppercase (not lowercased text)
                        judge_entry = f"{name}, {title}"
                        bench_judges.append(judge_entry)
    
    # Deduplicate
    seen: Set[str] = set()
    unique = []
    for judge in bench_judges:
        if judge and judge not in seen:
            seen.add(judge)
            unique.append(judge)
    
    return unique


def extract_author_judges(text: str) -> List[str]:
    """
    Extract the judge(s) who authored the judgment.
    
    The author is identified as the judge on the bench who does NOT have "I agree"
    statement at the end of the document. Concurring judges explicitly write "I agree".
    
    Args:
        text: Full text content of the court decision
        
    Returns:
        List of author judge names (typically the lone author)
    """
    # Find judges who agree
    agreeing_judges = _find_agreeing_judges(text)
    
    # Get all bench judges
    bench = extract_bench_judges(text)
    
    # Author = bench judges minus those who agree
    author_judges = []
    for judge in bench:
        if not _judge_agrees(judge, agreeing_judges):
            author_judges.append(judge)
    
    # Fallback: if all agree or nothing found, return first judge
    return author_judges if author_judges else (bench[:1] if bench else [])


def _judge_agrees(judge_name: str, agreeing_judges: Set[str]) -> bool:
    """Check if a judge is in the agreeing set using flexible matching."""
    normalized = _normalize_judge_name(judge_name)
    
    # Direct match
    if normalized in agreeing_judges:
        return True
    
    # Extract surname from judge name
    judge_surname = _extract_judge_surname(judge_name)
    
    if judge_surname:
        # Check if any agreeing judge has the same surname
        for agreeing in agreeing_judges:
            agreeing_surname = _extract_judge_surname(agreeing)
            if agreeing_surname and agreeing_surname == judge_surname:
                return True
    
    return False


def _extract_judge_surname(name: str) -> str:
    """Extract the surname from a judge name, removing titles and initials."""
    if not name:
        return ""
    
    # Remove titles and punctuation
    # Handle both "J.", "J", "CJ", "Chief Justice", etc.
    clean = re.sub(r',?\s*(?:J\.?|CJ|Chief Justice|PC|C\.J\.)\s*$', '', name, flags=re.IGNORECASE).strip()
    
    # Extract the last word (surname) - handles both "DHEERARATNE" and "R.N.M. DHEERARATNE"
    words = clean.split()
    surname = words[-1].lower() if words else ""
    
    # Remove trailing periods from surname (in case of "SILVA.")
    surname = surname.rstrip('.')
    
    return surname


def _find_agreeing_judges(text: str) -> Set[str]:
    """
    Find judges who explicitly state they agree with the judgment.
    
    Looks for patterns like:
    - "JUDGE NAME, J. - I agree" (same line)
    - "JUDGE NAME, J." followed by "I agree." on next line (separate lines)
    Note: "1" can be OCR error for "I"
    
    Args:
        text: Full text
        
    Returns:
        Set of normalized judge names who agree
    """
    agreeing = set()
    lines = text.split('\n')
    
    # Look in last 50 lines for "I agree" or "1 agree" statements
    for i, line in enumerate(lines[-50:]):
        # Match both "I agree" and "1 agree" (OCR confusion between 1 and I)
        if re.search(r'(?:I|1)\s+(?:agree|concur)', line, re.IGNORECASE):
            # First try: Same line pattern "NAME, J. - I agree"
            match = re.match(r'^\s*([A-Z][A-Z0-9\.\s\-,]*?)(?:\s*,?\s*(?:J\.|CJ|Chief Justice|PC|C\.J\.))?\s*[-–:]*\s*(?:I|1)\s+(?:agree|concur)', 
                            line, re.IGNORECASE)
            if match:
                judge_name = match.group(1).strip()
                normalized = _normalize_judge_name(judge_name)
                if normalized:
                    agreeing.add(normalized)
            else:
                # Second try: "I agree" is on this line, judge name might be on previous line
                # Look at previous line to extract judge name
                if i > 0:
                    prev_line = lines[-50:][i-1].strip()
                    # Check if previous line looks like a judge name line
                    # Pattern: Name optionally followed by title
                    judge_match = re.match(r'^\s*([A-Z][A-Z0-9\.\s\-,]*?)(?:\s*,?\s*(?:J\.|CJ|Chief Justice|PC|C\.J\.))?$', 
                                          prev_line, re.IGNORECASE)
                    if judge_match:
                        judge_name = judge_match.group(1).strip()
                        normalized = _normalize_judge_name(judge_name)
                        if normalized:
                            agreeing.add(normalized)
    
    return agreeing


def _parse_judge_line(line: str) -> List[str]:

    """
    Parse judge names from a single line.
    
    Handles formats like:
    - "H. A. G. DE SILVA. J.. AMERASINGHE. J. AND DHEERARATNE, J."
    - "A.G. DE SILVA, J., AMERASINGHE, J. AND DHEERARATNE, J."
    - Single judge per line: "Murdu N.B. Fernando, PC,J" or "L.T.B.Dehideniya, J"
    
    Strategy: Detect single-judge lines and handle them simply.
    For multi-judge lines, find patterns like "[Initials] [Names] [Title]".
    """
    judges = []
    
    # Normalize spaces
    line = re.sub(r'\s+', ' ', line.strip())
    
    # Normalize double periods
    line = re.sub(r'\.{2,}', '.', line)
    
    # Check if this looks like a single-judge line (no " AND " and ends with title)
    if ' AND ' not in line.upper():
        # Try matching: Full name (with possible initials) + title
        # Titles are short: J, PC, CJ, Judge, etc. (1-4 capital letters after comma/space)
        # For "Murdu N.B. Fernando, PC,J" the titles are "PC" and "J", not "N.B."
        match = re.match(r'^([A-Z][A-Za-z0-9\.\s\-]*[a-z])\s*[,\s]+([A-Z]{1,4}\.?(?:[,\s]+[A-Z]{1,4}\.?)*)\s*\.?\s*$', line)
        if match:
            name_part = match.group(1).strip()
            title_part = match.group(2).strip().rstrip('.')
            # Validate: name should contain a lowercase letter (actual name, not just initials)
            # and title should be short (typical judge titles)
            if len(name_part) > 2 and len(name_part) < 60 and len(title_part) > 0:
                # Clean up spacing in title
                titles = re.findall(r'[A-Z]{1,4}\.?', title_part)
                if titles and len(title_part) < 20:  # Sanity check: titles shouldn't be too long
                    formatted_title = ', '.join(t.rstrip('.') for t in titles)
                    return [f"{name_part}, {formatted_title}"]
    
    # Multi-judge extraction: replace AND with comma for splitting
    line = re.sub(r'\s+AND\s+', ', ', line, flags=re.IGNORECASE)
    
    # Find all judge patterns using regex
    # Pattern: Optional initials + Surname + optional title
    pattern = r'([A-Z](?:\.\s*)?(?:[A-Z]\.\s*)*[A-Z][a-z]+(?:\s+[A-Z][a-z\-]+)*)\s*\.?\s*(?:,?\s*(J\.|CJ|Chief Justice|PC|C\.J\.))?'
    
    matches = re.finditer(pattern, line, re.IGNORECASE)
    seen_positions = set()
    
    for match in matches:
        name = match.group(1).strip()
        title = match.group(2) if match.group(2) else ""
        
        # Skip if we already processed this position
        if match.start() in seen_positions:
            continue
        seen_positions.add(match.start())
        
        # Skip common non-judge words
        if name.upper() in ('AND', 'OR', 'THE', 'OF', 'BY'):
            continue
        
        # Clean up the name
        name = re.sub(r'\s+', ' ', name)
        
        # Only add if it's a reasonable judge name
        if len(name) > 1 and len(name) < 50:
            if title:
                judges.append(f"{name}, {title}")
            else:
                judges.append(name)
    
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for judge in judges:
        if judge not in seen:
            seen.add(judge)
            unique.append(judge)
    
    return unique


def _extract_judge_name_and_title(text: str) -> str:
    """Extract judge name + title from text like "A. G. DE SILVA, J." """
    text = text.strip().rstrip(',.')
    if not text or len(text) < 2:
        return ""
    
    # Match: capitals/dots (initials) + words + optional title
    # Handles: "A. G. DE SILVA, J." ,"AMERASINGHE, J", "Chief Justice P. S. de Silva"
    pattern = r'^([A-Z](?:\.\s*)?(?:[A-Z]\.\s*)*[A-Z][a-z]+(?:\s+[A-Z][a-z\-]+)*)\s*(?:,?\s*(J\.|CJ|Chief Justice|PC|C\.J\.))?'
    match = re.match(pattern, text, re.IGNORECASE)
    
    if match:
        name = match.group(1).strip()
        title = match.group(2) if match.group(2) else ""
        # Normalize spacing
        name = re.sub(r'\s+', ' ', name)
        return f"{name}, {title}" if title else name
    
    return ""


def _normalize_judge_name(name: str) -> str:
    """Normalize for comparison: remove titles, normalize formatting."""
    if not name:
        return ""
    
    # Remove titles
    norm = re.sub(r',?\s*(?:J\.|CJ|Chief Justice|PC|C\.J\.)\s*$', '', name, flags=re.IGNORECASE)
    
    # Remove OCR artifacts
    norm = re.sub(r'[\'":\.,;]+', '', norm)  # Remove common OCR errors
    
    # Normalize spacing: remove spaces after periods in initials for comparison
    # E.g., "H. A. G." becomes "h.a.g." for matching
    norm = re.sub(r'(?<!\w)([A-Z])\.(?:\s+(?=[A-Z]\.))?', r'\1.', norm, flags=re.IGNORECASE)
    
    # Normalize all whitespace to single spaces
    norm = re.sub(r'\s+', ' ', norm.strip())
    
    return norm.lower()
