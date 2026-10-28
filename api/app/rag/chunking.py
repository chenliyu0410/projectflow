def build_chunks(sections):
    chunks = []
    for section_index, section in enumerate(sections):
        text = section['text']
        for start in range(0, len(text), 1200):
            parent = text[start:start + 1200]
            parent_id = f's{section_index}:p{start}'
            for offset in range(0, len(parent), 320):
                child = parent[offset:offset + 400]
                if not child.strip():
                    continue
                locator = dict(section.get('locator') or {})
                # Public evidence expands to the parent, so its locator must describe that text.
                locator.update(start_char=start, end_char=start + len(parent))
                chunks.append(dict(text=child, parent_text=parent, parent_id=parent_id, locator=locator))
                if len(chunks) > 200:
                    raise ValueError('chunk_limit')
                if offset + 400 >= len(parent):
                    break
    return chunks
