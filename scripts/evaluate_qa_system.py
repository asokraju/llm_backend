#!/usr/bin/env python3
"""
Automated QA Evaluation Script for RAG System

This script loads questions from YAML files, queries the RAG system,
compares answers with ground truth, and builds a validated QA database.
"""

import asyncio
import sys
import os
import yaml
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

# Setup paths
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.append(project_root)

class QAEvaluator:
    """Automated QA evaluation system for RAG."""
    
    def __init__(self, working_dir: str = "ccdm_rag_database"):
        self.working_dir = working_dir
        self.lightrag = None
        self.results = []
        self.stats = {
            'total_questions': 0,
            'processed_questions': 0,
            'accurate_answers': 0,
            'relevant_answers': 0,
            'llm_verified_answers': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def initialize(self):
        """Initialize the RAG service."""
        try:
            from src.rag.lightrag_service import LightRAGService
            
            self.lightrag = LightRAGService(
                working_dir=self.working_dir,
                llm_model="qwen2.5:7b-instruct",
                embedding_model="nomic-embed-text"
            )
            
            await self.lightrag.initialize()
            print("✅ RAG system initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize RAG system: {e}")
            return False
    
    def load_questions(self, yaml_file: str) -> List[Dict[str, Any]]:
        """Load questions from YAML file."""
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                questions = yaml.safe_load(f)
            
            print(f"📚 Loaded {len(questions)} questions from {yaml_file}")
            return questions
            
        except Exception as e:
            print(f"❌ Error loading questions: {e}")
            return []
    
    async def query_rag_system(self, question: str) -> Dict[str, Any]:
        """Query the RAG system and return response with metadata."""
        try:
            start_time = time.time()
            response = await self.lightrag.query(question, mode="hybrid")
            end_time = time.time()
            
            return {
                'response': response,
                'response_time': end_time - start_time,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            return {
                'response': None,
                'response_time': 0,
                'success': False,
                'error': str(e)
            }
    
    async def verify_answer_with_llm(self, question: str, rag_response: str, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
        """Use the LightRAG LLM service to verify if RAG answer aligns with correct textbook answer."""
        
        # Extract ground truth information
        correct_option = ground_truth.get('answer', '').upper()
        options = ground_truth.get('options', {})
        explanation = ground_truth.get('explanation', '')
        
        # Format options for prompt
        options_text = "\n".join([f"{key.upper()}: {value}" for key, value in options.items()])
        
        # Create verification prompt
        verification_prompt = f"""You are an expert evaluator comparing two answers to a clinical data management question.

QUESTION:
{question}

MULTIPLE CHOICE OPTIONS:
{options_text}

TEXTBOOK CORRECT ANSWER: {correct_option}
EXPLANATION: {explanation}

RAG SYSTEM ANSWER:
{rag_response}

TASK:
Compare the RAG system answer with the textbook correct answer and explanation. Determine if they align conceptually, even if the wording is different.

Respond with a JSON object containing:
{{
    "alignment": "strong" | "moderate" | "weak" | "none",
    "reasoning": "brief explanation of why they align or don't align",
    "rag_identifies_correct_concept": true/false,
    "rag_contradicts_textbook": true/false,
    "confidence": 0.0-1.0
}}

Focus on conceptual alignment rather than exact wording. A strong alignment means the RAG answer would lead someone to the same correct understanding as the textbook answer."""
        
        try:
            # Use the LightRAG service's direct LLM method for verification
            verification_response = await self.lightrag.direct_llm_query(
                prompt=verification_prompt,
                system_prompt="You are an expert evaluator. Respond only with valid JSON."
            )
            
            # Parse the response
            verification_text = verification_response.strip()
            
            # Try to extract JSON from the response
            try:
                # Look for JSON in the response
                start_idx = verification_text.find('{')
                end_idx = verification_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx > start_idx:
                    json_text = verification_text[start_idx:end_idx]
                    verification_data = json.loads(json_text)
                else:
                    # Fallback - try the whole response
                    verification_data = json.loads(verification_text)
                
                return {
                    'llm_verification': verification_data,
                    'llm_success': True,
                    'llm_error': None
                }
                
            except json.JSONDecodeError:
                return {
                    'llm_verification': {'raw_response': verification_text},
                    'llm_success': False,
                    'llm_error': 'JSON parsing failed'
                }
                    
        except Exception as e:
            return {
                'llm_verification': None,
                'llm_success': False,
                'llm_error': str(e)
            }

    def evaluate_answer_quality(self, rag_response: str, ground_truth: Dict[str, Any], llm_verification: Dict[str, Any] = None) -> Dict[str, Any]:
        """Evaluate the quality of RAG response against ground truth."""
        
        # Extract ground truth information
        correct_option = ground_truth.get('answer', '').lower()
        options = ground_truth.get('options', {})
        explanation = ground_truth.get('explanation', '')
        
        # Get the correct answer text
        correct_answer_text = options.get(correct_option, '') if options else ''
        
        # Simple evaluation metrics
        evaluation = {
            'contains_correct_option': correct_option in rag_response.lower(),
            'contains_correct_text': self._text_similarity(rag_response, correct_answer_text) > 0.3,
            'contains_explanation_concepts': self._concept_overlap(rag_response, explanation) > 0.2,
            'response_length': len(rag_response),
            'is_relevant': self._is_response_relevant(rag_response, ground_truth['question']),
            'confidence_score': 0.0,
            'llm_verified': False
        }
        
        # Calculate base confidence score
        score = 0
        if evaluation['contains_correct_option']:
            score += 0.3
        if evaluation['contains_correct_text']:
            score += 0.2
        if evaluation['contains_explanation_concepts']:
            score += 0.2
        if evaluation['is_relevant']:
            score += 0.1
            
        # Enhanced scoring with LLM verification
        if llm_verification and llm_verification.get('llm_success'):
            verification_data = llm_verification.get('llm_verification', {})
            alignment = verification_data.get('alignment', 'none')
            identifies_correct = verification_data.get('rag_identifies_correct_concept', False)
            contradicts = verification_data.get('rag_contradicts_textbook', False)
            llm_confidence = verification_data.get('confidence', 0.0)
            
            # LLM verification scoring (worth up to 0.4 points)
            if alignment == 'strong':
                score += 0.4
                evaluation['llm_verified'] = True
            elif alignment == 'moderate':
                score += 0.3
                evaluation['llm_verified'] = True
            elif alignment == 'weak':
                score += 0.1
            
            # Bonus for identifying correct concept
            if identifies_correct:
                score += 0.1
                
            # Penalty for contradicting textbook
            if contradicts:
                score -= 0.2
                
            # Include LLM's confidence in evaluation
            evaluation['llm_alignment'] = alignment
            evaluation['llm_confidence'] = llm_confidence
            evaluation['identifies_correct_concept'] = identifies_correct
            evaluation['contradicts_textbook'] = contradicts
        
        evaluation['confidence_score'] = min(max(score, 0.0), 1.0)
        
        # Determine if answer is accurate (threshold: 0.6)
        evaluation['is_accurate'] = evaluation['confidence_score'] >= 0.6
        
        return evaluation
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity based on word overlap."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _concept_overlap(self, response: str, explanation: str) -> float:
        """Check overlap of key concepts between response and explanation."""
        if not response or not explanation:
            return 0.0
        
        # Extract key concepts (simple approach)
        response_words = set(w.lower() for w in response.split() if len(w) > 4)
        explanation_words = set(w.lower() for w in explanation.split() if len(w) > 4)
        
        if not explanation_words:
            return 0.0
        
        overlap = response_words.intersection(explanation_words)
        return len(overlap) / len(explanation_words)
    
    def _is_response_relevant(self, response: str, question: str) -> bool:
        """Check if response is relevant to the question."""
        if not response or len(response) < 50:
            return False
        
        # Extract key terms from question
        question_terms = [w.lower() for w in question.split() if len(w) > 3]
        response_lower = response.lower()
        
        # Check if response contains at least 2 key terms from question
        matches = sum(1 for term in question_terms if term in response_lower)
        return matches >= 2
    
    async def process_question(self, qa_item: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Process a single question through the RAG system."""
        question = qa_item['question']
        
        print(f"📝 Processing question {index + 1}: {question[:60]}...")
        
        # Query RAG system
        rag_result = await self.query_rag_system(question)
        
        if not rag_result['success']:
            print(f"   ❌ RAG query failed: {rag_result['error']}")
            return {
                'question_index': index,
                'question': question,
                'ground_truth': qa_item,
                'rag_response': None,
                'evaluation': None,
                'llm_verification': None,
                'error': rag_result['error'],
                'timestamp': datetime.now().isoformat()
            }
        
        # Verify answer with LLM
        print(f"   🔍 Verifying with LLM...")
        llm_result = await self.verify_answer_with_llm(question, rag_result['response'], qa_item)
        
        # Evaluate answer quality with LLM verification
        evaluation = self.evaluate_answer_quality(rag_result['response'], qa_item, llm_result)
        
        # Create result record
        result = {
            'question_index': index,
            'question': question,
            'ground_truth': {
                'answer': qa_item.get('answer'),
                'explanation': qa_item.get('explanation'),
                'difficulty': qa_item.get('difficulty'),
                'subtopic': qa_item.get('subtopic'),
                'options': qa_item.get('options', {})
            },
            'rag_response': rag_result['response'],
            'rag_metadata': {
                'response_time': rag_result['response_time'],
                'response_length': len(rag_result['response'])
            },
            'llm_verification': llm_result,
            'evaluation': evaluation,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Print evaluation summary
        confidence = evaluation['confidence_score']
        accuracy_icon = "✅" if evaluation['is_accurate'] else "❌"
        relevance_icon = "✅" if evaluation['is_relevant'] else "❌"
        llm_icon = "🤖" if evaluation.get('llm_verified') else "⚪"
        llm_alignment = evaluation.get('llm_alignment', 'unknown')
        
        print(f"   {accuracy_icon} Accuracy: {confidence:.2f} | {relevance_icon} Relevant | {llm_icon} LLM: {llm_alignment} | Time: {rag_result['response_time']:.2f}s")
        
        return result
    
    async def evaluate_question_bank(self, yaml_file: str, max_questions: Optional[int] = None) -> Dict[str, Any]:
        """Evaluate entire question bank."""
        print(f"🔍 Starting QA Evaluation: {yaml_file}")
        print("=" * 60)
        
        self.stats['start_time'] = datetime.now()
        
        # Load questions
        questions = self.load_questions(yaml_file)
        if not questions:
            return {'error': 'Failed to load questions'}
        
        # Limit questions if specified
        if max_questions:
            questions = questions[:max_questions]
            print(f"🔢 Limited to first {max_questions} questions")
        
        self.stats['total_questions'] = len(questions)
        
        # Process each question
        for i, qa_item in enumerate(questions):
            result = await self.process_question(qa_item, i)
            self.results.append(result)
            
            # Update stats
            self.stats['processed_questions'] += 1
            if result['evaluation'] and result['evaluation']['is_accurate']:
                self.stats['accurate_answers'] += 1
            if result['evaluation'] and result['evaluation']['is_relevant']:
                self.stats['relevant_answers'] += 1
            if result['evaluation'] and result['evaluation'].get('llm_verified'):
                self.stats['llm_verified_answers'] += 1
            
            # Progress update
            if (i + 1) % 10 == 0:
                accuracy_rate = (self.stats['accurate_answers'] / self.stats['processed_questions']) * 100
                print(f"📊 Progress: {i + 1}/{len(questions)} | Accuracy: {accuracy_rate:.1f}%")
        
        self.stats['end_time'] = datetime.now()
        
        return self.generate_final_report()
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive evaluation report."""
        total_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        # Calculate metrics
        accuracy_rate = (self.stats['accurate_answers'] / self.stats['processed_questions']) * 100 if self.stats['processed_questions'] > 0 else 0
        relevance_rate = (self.stats['relevant_answers'] / self.stats['processed_questions']) * 100 if self.stats['processed_questions'] > 0 else 0
        avg_response_time = sum(r['rag_metadata']['response_time'] for r in self.results if r['rag_response']) / len([r for r in self.results if r['rag_response']])
        
        # Analyze by difficulty
        difficulty_stats = {}
        for result in self.results:
            if result['evaluation']:
                difficulty = result['ground_truth']['difficulty']
                if difficulty not in difficulty_stats:
                    difficulty_stats[difficulty] = {'total': 0, 'accurate': 0}
                difficulty_stats[difficulty]['total'] += 1
                if result['evaluation']['is_accurate']:
                    difficulty_stats[difficulty]['accurate'] += 1
        
        # Analyze by subtopic
        subtopic_stats = {}
        for result in self.results:
            if result['evaluation']:
                subtopic = result['ground_truth']['subtopic']
                if subtopic not in subtopic_stats:
                    subtopic_stats[subtopic] = {'total': 0, 'accurate': 0}
                subtopic_stats[subtopic]['total'] += 1
                if result['evaluation']['is_accurate']:
                    subtopic_stats[subtopic]['accurate'] += 1
        
        report = {
            'summary': {
                'total_questions': self.stats['total_questions'],
                'processed_questions': self.stats['processed_questions'],
                'accuracy_rate': accuracy_rate,
                'relevance_rate': relevance_rate,
                'avg_response_time': avg_response_time,
                'total_evaluation_time': total_time
            },
            'difficulty_breakdown': {
                diff: {
                    'accuracy_rate': (stats['accurate'] / stats['total']) * 100,
                    'count': stats['total']
                }
                for diff, stats in difficulty_stats.items()
            },
            'subtopic_breakdown': {
                topic: {
                    'accuracy_rate': (stats['accurate'] / stats['total']) * 100,
                    'count': stats['total']
                }
                for topic, stats in subtopic_stats.items()
            },
            'timestamp': datetime.now().isoformat(),
            'detailed_results': self.results
        }
        
        return report
    
    def save_results(self, report: Dict[str, Any], output_file: str):
        """Save evaluation results to JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"💾 Results saved to: {output_file}")
        except Exception as e:
            print(f"❌ Error saving results: {e}")
    
    def print_summary(self, report: Dict[str, Any]):
        """Print evaluation summary."""
        summary = report['summary']
        
        print("\n" + "=" * 60)
        print("📊 QA EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Total Questions: {summary['total_questions']}")
        print(f"Processed: {summary['processed_questions']}")
        print(f"Accuracy Rate: {summary['accuracy_rate']:.1f}%")
        print(f"Relevance Rate: {summary['relevance_rate']:.1f}%")
        print(f"Avg Response Time: {summary['avg_response_time']:.2f}s")
        print(f"Total Time: {summary['total_evaluation_time']:.1f}s")
        
        print(f"\n📈 Performance by Difficulty:")
        for difficulty, stats in report['difficulty_breakdown'].items():
            print(f"  {difficulty.capitalize()}: {stats['accuracy_rate']:.1f}% ({stats['count']} questions)")
        
        print(f"\n📑 Top Performing Subtopics:")
        sorted_topics = sorted(report['subtopic_breakdown'].items(), 
                              key=lambda x: x[1]['accuracy_rate'], reverse=True)
        for topic, stats in sorted_topics[:5]:
            print(f"  {topic}: {stats['accuracy_rate']:.1f}% ({stats['count']} questions)")
        
        print("=" * 60)
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.lightrag:
            await self.lightrag.close()

async def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate RAG system with question bank")
    parser.add_argument("--yaml_file", 
                       default="data/question_bank/05_Data_Privacy.yaml",
                       help="Path to YAML question bank file")
    parser.add_argument("--output", 
                       default="qa_evaluation_results.json",
                       help="Output file for results")
    parser.add_argument("--max_questions", type=int,
                       help="Maximum number of questions to process")
    parser.add_argument("--working_dir",
                       default="ccdm_rag_database",
                       help="RAG database directory")
    
    args = parser.parse_args()
    
    # Initialize evaluator
    evaluator = QAEvaluator(working_dir=args.working_dir)
    
    try:
        # Initialize RAG system
        if not await evaluator.initialize():
            return 1
        
        # Run evaluation
        report = await evaluator.evaluate_question_bank(
            yaml_file=args.yaml_file,
            max_questions=args.max_questions
        )
        
        if 'error' in report:
            print(f"❌ Evaluation failed: {report['error']}")
            return 1
        
        # Save and display results
        evaluator.save_results(report, args.output)
        evaluator.print_summary(report)
        
        # Create validated QA database (only accurate answers)
        validated_qa = [
            {
                'question': result['question'],
                'rag_answer': result['rag_response'],
                'ground_truth': result['ground_truth'],
                'confidence_score': result['evaluation']['confidence_score'],
                'subtopic': result['ground_truth']['subtopic']
            }
            for result in report['detailed_results']
            if result['evaluation'] and result['evaluation']['is_accurate']
        ]
        
        validated_file = args.output.replace('.json', '_validated_qa.json')
        with open(validated_file, 'w', encoding='utf-8') as f:
            json.dump(validated_qa, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Validated QA database saved: {validated_file}")
        print(f"📚 Contains {len(validated_qa)} high-quality Q&A pairs")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ Evaluation interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    finally:
        await evaluator.cleanup()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)