# app/services/context.py
"""
Universal context tracking service for maintaining conversation focus across any product domain.
"""
from typing import Dict, List, Tuple, Any, Optional
import re
from collections import defaultdict

class EntityTracker:
    """Tracks entities and references throughout a conversation."""
    
    def __init__(self):
        self.entities = defaultdict(dict)  # Tracks all mentioned entities
        self.primary_entity = None         # Current focus entity
        self.secondary_entities = []       # Related entities in current context
        self.last_update_turn = 0          # Conversation turn counter
        self.attributes_discussed = defaultdict(list)  # Tracks attributes per entity
    
    def update(self, entity: str, confidence: float, turn: int, 
               attributes: Optional[List[str]] = None) -> None:
        """Update tracked entity with new information"""
        self.entities[entity]['last_seen'] = turn
        self.entities[entity]['confidence'] = confidence
        
        # Update primary entity if this one has higher confidence
        if not self.primary_entity or confidence > self.entities.get(
                self.primary_entity, {}).get('confidence', 0):
            if self.primary_entity:
                self.secondary_entities.append(self.primary_entity)
            self.primary_entity = entity
        
        # Track attributes being discussed about this entity
        if attributes:
            self.attributes_discussed[entity].extend(
                [attr for attr in attributes if attr not in self.attributes_discussed[entity]])

class ConversationContext:
    """Advanced context manager for multi-domain product conversations."""
    
    def __init__(self):
        self.user_contexts: Dict[str, Dict] = {}
        self.max_history_turns = 5  # Maximum conversation turns to consider
        
        # Common attribute types - extend based on your product domains
        self.attribute_patterns = {
            'duration': r'\b(?:last|duration|lifetime|longevity|lifespan)\b',
            'performance': r'\b(?:speed|power|performance|efficiency|output)\b',
            'price': r'\b(?:cost|price|expensive|cheap|affordable)\b',
            'comparison': r'\b(?:better|worse|compared|difference|versus|vs)\b',
            'specification': r'\b(?:spec|specification|feature|capability)\b'
        }
        
        # Entity types for different product categories
        self.entity_patterns = {
            'product': r'\b([A-Z0-9][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*)\s+(?:product|model|system|kit)\b',
            'electronics': r'\b([A-Z0-9][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*)\s+(?:device|gadget|charger)\b',
            'energy': r'\b([A-Z0-9][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*)\s+(?:battery|panel|generator|inverter)\b',
            'vehicle': r'\b([A-Z0-9][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*)\s+(?:bike|scooter|vehicle|cycle)\b',
            'generic': r'\b([A-Z0-9][A-Za-z0-9-]+(?:-\d+)?)\b'
        }
        
        # Common pronouns to resolve
        self.pronoun_patterns = [
            (r'\b(it|this|that)\b', 'singular'),
            (r'\b(they|them|these|those)\b', 'plural'),
            (r'\b(this product|this model|this device)\b', 'specific')
        ]
    
    def _extract_entities(self, text: str) -> List[Tuple[str, str, float]]:
        """
        Extract potential product entities from text.
        Returns: List of (entity, type, confidence) tuples
        """
        found_entities = []
        
        # Extract entities using patterns
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Calculate confidence based on match details
                confidence = 0.7
                # Boost confidence for product names with numbers/identifiers
                if re.search(r'[A-Z]-\d+|[A-Z]\d+|[A-Z]{2,}', match.group(1)):
                    confidence += 0.2
                # Boost confidence for capitalized terms
                if match.group(1)[0].isupper():
                    confidence += 0.1
                    
                found_entities.append((match.group(0), entity_type, confidence))
        
        return found_entities
    
    def _extract_attributes(self, text: str) -> List[str]:
        """Extract attributes being discussed about entities"""
        attributes = []
        for attr_type, pattern in self.attribute_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                attributes.append(attr_type)
        return attributes
    
    def track_exchange(self, user_id: str, question: str, answer: str, turn: int = 0) -> None:
        """
        Process a conversation exchange to update context.
        
        Args:
            user_id: Unique user identifier
            question: User's question
            answer: System's answer
            turn: Conversation turn number (or 0 for auto-increment)
        """
        # Initialize user context if needed
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                'tracker': EntityTracker(),
                'turns': 0,
                'history': [],
                'last_question': '',
                'last_pronoun_resolution': None
            }
        
        context = self.user_contexts[user_id]
        
        # Auto-increment turn if not provided
        if turn == 0:
            context['turns'] += 1
            turn = context['turns']
        
        # Extract entities from both question and answer
        combined_text = question + " " + answer
        found_entities = self._extract_entities(combined_text)
        attributes = self._extract_attributes(combined_text)
        
        # Update entity tracker
        for entity, entity_type, confidence in found_entities:
            context['tracker'].update(entity, confidence, turn, attributes)
        
        # Store this exchange in history
        context['history'].append({
            'turn': turn,
            'question': question,
            'answer': answer,
            'entities': [e[0] for e in found_entities],
            'attributes': attributes
        })
        
        # Limit history size
        if len(context['history']) > self.max_history_turns:
            context['history'] = context['history'][-self.max_history_turns:]
        
        context['last_question'] = question
    
    def resolve_references(self, user_id: str, current_question: str) -> str:
        """
        Resolve pronoun references based on conversation context.
        
        Args:
            user_id: User identifier
            current_question: Current question with potential pronouns
            
        Returns:
            Question with pronouns resolved where possible
        """
        if user_id not in self.user_contexts:
            return current_question
        
        context = self.user_contexts[user_id]
        tracker = context['tracker']
        
        if not tracker.primary_entity:
            return current_question
        
        resolved_question = current_question
        resolution_applied = False
        
        # Try to resolve pronouns
        for pattern, pronoun_type in self.pronoun_patterns:
            if re.search(pattern, resolved_question, re.IGNORECASE):
                if pronoun_type in ('singular', 'specific') and tracker.primary_entity:
                    resolved_question = re.sub(
                        pattern, 
                        tracker.primary_entity, 
                        resolved_question, 
                        flags=re.IGNORECASE
                    )
                    resolution_applied = True
                    
                elif pronoun_type == 'plural' and (tracker.secondary_entities or tracker.primary_entity):
                    # For plural pronouns, try to use secondary entities if available
                    if tracker.secondary_entities:
                        replacement = f"{tracker.primary_entity} and {tracker.secondary_entities[0]}"
                    else:
                        replacement = tracker.primary_entity  # Fallback to primary
                    
                    resolved_question = re.sub(
                        pattern, 
                        replacement, 
                        resolved_question, 
                        flags=re.IGNORECASE
                    )
                    resolution_applied = True
        
        # Track the resolution for later reference
        if resolution_applied:
            context['last_pronoun_resolution'] = {
                'original': current_question,
                'resolved': resolved_question,
                'primary_entity': tracker.primary_entity
            }
            
        return resolved_question
    
    def create_context_directive(self, user_id: str) -> str:
        """
        Generate a context directive for the LLM to maintain topic focus.
        
        Args:
            user_id: User identifier
            
        Returns:
            Contextual directive for the system prompt
        """
        if user_id not in self.user_contexts:
            return ""
        
        context = self.user_contexts[user_id]
        tracker = context['tracker']
        
        if not tracker.primary_entity:
            return ""
        
        # Build contextual directive
        directive = f"\n\nCONTEXT DIRECTIVE: The current conversation is focused on {tracker.primary_entity}."
        
        # Add recently discussed attributes if any
        if tracker.primary_entity in tracker.attributes_discussed:
            attrs = tracker.attributes_discussed[tracker.primary_entity]
            if attrs:
                recent_attrs = attrs[-3:] if len(attrs) > 3 else attrs
                directive += f" The user has been asking about its {', '.join(recent_attrs)}."
        
        # Add secondary entities if relevant
        if tracker.secondary_entities:
            directive += f" Other relevant products mentioned include: {', '.join(tracker.secondary_entities[:2])}."
            
        # Add pronoun resolution guidance
        directive += f"\nWhen the user uses pronouns like 'it', 'this', or 'that', they are most likely referring to {tracker.primary_entity} unless clearly indicated otherwise."
        
        return directive
    
    def filter_relevant_history(self, user_id: str, full_history: str) -> str:
        """
        Filter conversation history to maintain relevance to current context.
        
        Args:
            user_id: User identifier
            full_history: Complete conversation history string
            
        Returns:
            Filtered history focused on current topic
        """
        if user_id not in self.user_contexts or not full_history:
            return full_history
            
        context = self.user_contexts[user_id]
        tracker = context['tracker']
        
        # Return full history for short conversations
        history_entries = full_history.strip().split('\n')
        qa_pairs = len(history_entries) // 2
        if qa_pairs <= 3:
            return full_history
            
        # Build relevant history when we have a primary entity
        if tracker.primary_entity:
            filtered_lines = []
            entity_lower = tracker.primary_entity.lower()
            
            # Always include the most recent exchange
            if len(history_entries) >= 2:
                filtered_lines.extend(history_entries[-2:])
            
            # Add exchanges about the primary entity
            for i in range(0, len(history_entries)-2, 2):
                q_line = history_entries[i]
                a_line = history_entries[i+1] if i+1 < len(history_entries) else ""
                
                if entity_lower in q_line.lower() or entity_lower in a_line.lower():
                    # Avoid duplicates
                    if q_line not in filtered_lines:
                        filtered_lines.insert(0, q_line)
                        filtered_lines.insert(1, a_line)
            
            # If we have resolved pronouns previously, include that exchange
            if context.get('last_pronoun_resolution'):
                res = context['last_pronoun_resolution']
                for i in range(0, len(history_entries)-2, 2):
                    q_line = history_entries[i]
                    a_line = history_entries[i+1] if i+1 < len(history_entries) else ""
                    
                    if res['original'] in q_line:
                        if q_line not in filtered_lines:
                            filtered_lines.insert(0, q_line)
                            filtered_lines.insert(1, a_line)
            
            # Limit to maximum 4 QA pairs
            if len(filtered_lines) > 8:
                filtered_lines = filtered_lines[:8]
                
            if filtered_lines:
                return "\n".join(filtered_lines)
        
        # Default: return the most recent exchanges
        return "\n".join(history_entries[-6:]) if len(history_entries) > 6 else full_history