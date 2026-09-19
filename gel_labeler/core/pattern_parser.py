import re
from typing import List

MAX_RANGE_SPAN = 500
MAX_TOTAL_LABELS = 1000

def parse_label_pattern(pattern: str) -> List[str]:
    """Parses a lane pattern string into a list of individual lane labels.
    
    Supports:
        - Commas for separating labels (e.g. 'Ladder, NC, PC')
        - Ranges of numbers (e.g. '1-26' expands to '1', '2', ..., '26')
        - Ranges with letter prefixes (e.g. 'S111-S119' expands to 'S111', ..., 'S119')
        - Literal values (e.g. 'Ladder', 'P1', 'Control')
        
    Example:
        Input: 'Ladder, P1, P2, 1-6, S111-S113, P3'
        Output: ['Ladder', 'P1', 'P2', '1', '2', '3', '4', '5', '6', 'S111', 'S112', 'S113', 'P3']
    """
    if not pattern or not pattern.strip():
        return []
        
    parts = [p.strip() for p in pattern.split(",") if p.strip()]
    labels = []
    
    for part in parts:
        if len(labels) >= MAX_TOTAL_LABELS:
            break

        # Check if this part defines a range (has a hyphen)
        if '-' in part:
            subparts = part.split('-')
            if len(subparts) == 2:
                start_str = subparts[0].strip()
                end_str = subparts[1].strip()
                
                # Case 1: Simple numeric range (e.g. '1-26' or '26-1')
                if start_str.isdigit() and end_str.isdigit():
                    start = int(start_str)
                    end = int(end_str)
                    
                    # Cap range span to avoid resource exhaustion
                    if abs(end - start) + 1 > MAX_RANGE_SPAN:
                        end = start + MAX_RANGE_SPAN - 1 if start <= end else start - MAX_RANGE_SPAN + 1
                        
                    step = 1 if start <= end else -1
                    for num in range(start, end + step, step):
                        labels.append(str(num))
                        if len(labels) >= MAX_TOTAL_LABELS:
                            break
                    continue
                    
                # Case 2: Letter-prefixed range (e.g. 'S111-S119' or 'L1-L30')
                m_start = re.match(r"^([a-zA-Z_]+)(\d+)$", start_str)
                m_end = re.match(r"^([a-zA-Z_]+)(\d+)$", end_str)
                
                if m_start and m_end and m_start.group(1) == m_end.group(1):
                    prefix = m_start.group(1)
                    start_val = int(m_start.group(2))
                    end_val = int(m_end.group(2))
                    
                    # Cap range span to avoid resource exhaustion
                    if abs(end_val - start_val) + 1 > MAX_RANGE_SPAN:
                        end_val = start_val + MAX_RANGE_SPAN - 1 if start_val <= end_val else start_val - MAX_RANGE_SPAN + 1
                    
                    # Pad numbers to keep visual consistency if specified (e.g. L01-L09)
                    start_len = len(m_start.group(2))
                    end_len = len(m_end.group(2))
                    pad_len = max(start_len, end_len) if start_str.startswith('0') or end_str.startswith('0') else 0
                    
                    step = 1 if start_val <= end_val else -1
                    for val in range(start_val, end_val + step, step):
                        num_str = str(val).zfill(pad_len) if pad_len > 0 else str(val)
                        labels.append(f"{prefix}{num_str}")
                        if len(labels) >= MAX_TOTAL_LABELS:
                            break
                    continue
                    
        # Case 3: Literal text (e.g. 'Ladder', 'P1', 'PC', 'NC')
        labels.append(part)
        
    return labels[:MAX_TOTAL_LABELS]
