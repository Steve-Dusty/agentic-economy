/**
 * Smart Artifact Matcher
 *
 * High-precision artifact matching using word-by-word keyword analysis
 * combined with semantic similarity. Defaults to 0 artifacts unless
 * there's a strong match (confidence >= 0.85).
 */

import { artifactService } from './artifact-service';
import { generateEmbedding, cosineSimilarity, formatArtifactsForContext } from './artifact-matcher';
import type { ArtifactWithEntries } from './types';
import type { ChatMessage } from '@/lib/ai-assistant/types';

/**
 * Options for smart artifact matching
 */
export interface SmartMatchOptions {
  userId: string;
  message: string;
  conversationHistory?: ChatMessage[];
  manualArtifactIds?: string[];
  maxArtifacts?: number;
  minConfidence?: number;
}

/**
 * Result from matching with confidence scores (exported for use in API)
 */
export interface MatchResult {
  artifact: ArtifactWithEntries;
  confidence: number;
  keywordScore: number;
  semanticScore: number;
}

/**
 * Common stop words to filter out
 */
const STOP_WORDS = new Set([
  // Articles and determiners
  'the', 'a', 'an', 'this', 'that', 'these', 'those',
  // Pronouns
  'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
  'my', 'your', 'his', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
  // Prepositions
  'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into',
  'over', 'after', 'under', 'between', 'out', 'against', 'during', 'without', 'before',
  // Conjunctions
  'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either', 'neither',
  // Common verbs
  'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
  'do', 'does', 'did', 'doing', 'will', 'would', 'could', 'should', 'may', 'might',
  'must', 'can', 'shall',
  // Common words in AI chat context
  'please', 'help', 'want', 'need', 'like', 'make', 'create', 'workflow', 'use',
  'using', 'get', 'give', 'take', 'let', 'know', 'think', 'see', 'look', 'find',
  'show', 'tell', 'ask', 'said', 'say', 'just', 'also', 'well', 'very', 'really',
  'some', 'any', 'all', 'each', 'every', 'most', 'other', 'such', 'only', 'own',
  'same', 'than', 'too', 'now', 'here', 'there', 'when', 'where', 'why', 'how',
  'what', 'which', 'who', 'whom', 'whose',
]);

/**
 * Extract keywords from a message using word-by-word analysis
 */
export function extractKeywords(
  message: string,
  conversationHistory: ChatMessage[] = []
): string[] {
  // Combine message with recent conversation context (last 2 messages)
  const recentContext = conversationHistory
    .slice(-2)
    .map((m) => m.content)
    .join(' ');
  const fullText = `${message} ${recentContext}`;

  // Tokenize: lowercase, remove punctuation, split by whitespace
  const words = fullText
    .toLowerCase()
    .replace(/[^\w\s-]/g, ' ')
    .split(/\s+/)
    .filter((word) => word.length > 2); // Minimum 3 characters

  // Filter stop words
  const meaningfulWords = words.filter((word) => !STOP_WORDS.has(word));

  // Extract bigrams (two-word phrases) for compound terms
  const bigrams = extractBigrams(meaningfulWords);

  // Combine and deduplicate
  const allKeywords = [...new Set([...meaningfulWords, ...bigrams])];

  return allKeywords;
}

/**
 * Extract bigrams (two consecutive words) that might be meaningful phrases
 */
function extractBigrams(words: string[]): string[] {
  const bigrams: string[] = [];

  for (let i = 0; i < words.length - 1; i++) {
    const bigram = `${words[i]} ${words[i + 1]}`;
    // Only include bigrams where both words are reasonably long
    if (words[i].length >= 3 && words[i + 1].length >= 3) {
      bigrams.push(bigram);
    }
  }

  return bigrams;
}

/**
 * Calculate keyword overlap score between keywords and artifact content
 */
export function calculateKeywordScore(
  keywords: string[],
  artifact: ArtifactWithEntries
): number {
  if (keywords.length === 0) return 0;

  // Build artifact text corpus
  const artifactTextParts: string[] = [
    artifact.title,
    artifact.summary || '',
    ...artifact.entries.slice(0, 5).map((e) => e.content), // Recent 5 entries
  ];
  const artifactText = artifactTextParts.join(' ').toLowerCase();

  // Tokenize artifact text into a set of words
  const artifactWords = new Set(
    artifactText.replace(/[^\w\s-]/g, ' ').split(/\s+/)
  );

  let matchScore = 0;
  let totalWeight = 0;

  for (const keyword of keywords) {
    // Weight longer keywords more heavily (they're more specific)
    const weight = keyword.length > 6 ? 2 : keyword.length > 4 ? 1.5 : 1;
    totalWeight += weight;

    // Check for exact match
    if (artifactWords.has(keyword)) {
      matchScore += weight;
    } else if (keyword.includes(' ')) {
      // For bigrams, check if the phrase exists in the text
      if (artifactText.includes(keyword)) {
        matchScore += weight;
      }
    } else {
      // Check for partial match (substring)
      for (const word of artifactWords) {
        if (
          word.length >= 4 &&
          (word.includes(keyword) || keyword.includes(word))
        ) {
          matchScore += weight * 0.5;
          break;
        }
      }
    }
  }

  return totalWeight > 0 ? matchScore / totalWeight : 0;
}

/**
 * Calculate semantic similarity between message and artifact
 */
async function calculateSemanticScore(
  messageEmbedding: number[],
  artifact: ArtifactWithEntries
): Promise<number> {
  // Build text from artifact for embedding comparison
  const artifactText = [
    artifact.title,
    artifact.summary || '',
    ...artifact.entries.slice(0, 3).map((e) => e.content),
  ].join('\n\n');

  const artifactEmbedding = await generateEmbedding(artifactText);

  if (!artifactEmbedding) {
    return 0;
  }

  return cosineSimilarity(messageEmbedding, artifactEmbedding);
}

/**
 * Combine keyword and semantic scores
 * Uses a formula that requires BOTH scores to be reasonably high
 */
export function combineScores(
  keywordScore: number,
  semanticScore: number
): number {
  // If either score is 0, no match
  if (keywordScore === 0 || semanticScore === 0) {
    return 0;
  }

  // Weighted combination: keyword 40%, semantic 60%
  const weightedScore = keywordScore * 0.4 + semanticScore * 0.6;

  // Apply penalty if keyword score is too low (need actual keyword matches)
  if (keywordScore < 0.25) {
    return weightedScore * 0.5;
  }

  return weightedScore;
}

/**
 * Find artifacts for a message with high precision matching
 *
 * This function defaults to returning NO artifacts unless there's a very strong match.
 * It analyzes the message word-by-word to find artifacts that deeply match the content.
 */
export async function findArtifactsForMessage(
  options: SmartMatchOptions
): Promise<ArtifactWithEntries[]> {
  const {
    userId,
    message,
    conversationHistory = [],
    manualArtifactIds = [],
    maxArtifacts = 2,
    minConfidence = 0.70, // Lowered threshold for better recall
  } = options;

  // 1. Always include manually selected artifacts first
  const manualArtifacts: ArtifactWithEntries[] = [];
  for (const id of manualArtifactIds) {
    const artifact = await artifactService.getWithEntries(id);
    if (artifact && artifact.userId === userId) {
      manualArtifacts.push(artifact);
    }
  }

  // If max artifacts reached with manual selection, return early
  if (manualArtifacts.length >= maxArtifacts) {
    return manualArtifacts.slice(0, maxArtifacts);
  }

  // 2. Extract keywords from message (deep word-by-word analysis)
  const keywords = extractKeywords(message, conversationHistory);

  // If no meaningful keywords, return only manual artifacts
  if (keywords.length === 0) {
    return manualArtifacts;
  }

  // 3. Get all user artifacts
  const allArtifacts = await artifactService.getByUserId(userId);
  const excludeIds = new Set(manualArtifactIds);
  const candidateArtifacts = allArtifacts.filter((a) => !excludeIds.has(a.id));

  if (candidateArtifacts.length === 0) {
    return manualArtifacts;
  }

  // 4. Generate embedding for the message
  const messageEmbedding = await generateEmbedding(message);

  // 5. Score each artifact
  const matches: MatchResult[] = [];

  for (const artifact of candidateArtifacts) {
    const artifactWithEntries = await artifactService.getWithEntries(artifact.id);
    if (!artifactWithEntries) continue;

    // Calculate keyword score
    const keywordScore = calculateKeywordScore(keywords, artifactWithEntries);

    // Skip if keyword score is too low (no point calculating semantic)
    if (keywordScore < 0.2) continue;

    // Calculate semantic score
    const semanticScore = messageEmbedding
      ? await calculateSemanticScore(messageEmbedding, artifactWithEntries)
      : 0;

    // Combine scores
    const confidence = combineScores(keywordScore, semanticScore);

    if (confidence >= minConfidence) {
      matches.push({
        artifact: artifactWithEntries,
        confidence,
        keywordScore,
        semanticScore,
      });
    }
  }

  // 6. Sort by confidence and take top results
  matches.sort((a, b) => b.confidence - a.confidence);
  const remainingSlots = maxArtifacts - manualArtifacts.length;
  const autoMatched = matches.slice(0, remainingSlots).map((m) => m.artifact);

  return [...manualArtifacts, ...autoMatched];
}

/**
 * Find artifacts with confidence metadata (for injection indicator UI)
 */
export async function findArtifactsWithConfidence(
  options: SmartMatchOptions
): Promise<{ artifact: ArtifactWithEntries; confidence: number }[]> {
  const {
    userId,
    message,
    conversationHistory = [],
    manualArtifactIds = [],
    maxArtifacts = 2,
    minConfidence = 0.70,
  } = options;

  const manualArtifacts: { artifact: ArtifactWithEntries; confidence: number }[] = [];
  for (const id of manualArtifactIds) {
    const artifact = await artifactService.getWithEntries(id);
    if (artifact && artifact.userId === userId) {
      manualArtifacts.push({ artifact, confidence: 1.0 });
    }
  }

  if (manualArtifacts.length >= maxArtifacts) {
    return manualArtifacts.slice(0, maxArtifacts);
  }

  const keywords = extractKeywords(message, conversationHistory);
  if (keywords.length === 0) return manualArtifacts;

  const allArtifacts = await artifactService.getByUserId(userId);
  const excludeIds = new Set(manualArtifactIds);
  const candidateArtifacts = allArtifacts.filter((a) => !excludeIds.has(a.id));
  if (candidateArtifacts.length === 0) return manualArtifacts;

  const messageEmbedding = await generateEmbedding(message);
  const matches: MatchResult[] = [];

  for (const artifact of candidateArtifacts) {
    const artifactWithEntries = await artifactService.getWithEntries(artifact.id);
    if (!artifactWithEntries) continue;

    const keywordScore = calculateKeywordScore(keywords, artifactWithEntries);
    if (keywordScore < 0.2) continue;

    const semanticScore = messageEmbedding
      ? await calculateSemanticScore(messageEmbedding, artifactWithEntries)
      : 0;

    const confidence = combineScores(keywordScore, semanticScore);

    if (confidence >= minConfidence) {
      matches.push({ artifact: artifactWithEntries, confidence, keywordScore, semanticScore });
    }
  }

  matches.sort((a, b) => b.confidence - a.confidence);
  const remainingSlots = maxArtifacts - manualArtifacts.length;
  const autoMatched = matches.slice(0, remainingSlots).map((m) => ({
    artifact: m.artifact,
    confidence: m.confidence,
  }));

  return [...manualArtifacts, ...autoMatched];
}

// Re-export formatArtifactsForContext for convenience
export { formatArtifactsForContext };
