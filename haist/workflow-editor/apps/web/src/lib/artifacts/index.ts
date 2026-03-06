/**
 * Artifacts Module
 *
 * Topic-based context storage that accumulates knowledge over time.
 */

export * from './types';
export { artifactService } from './artifact-service';
export {
  generateEmbedding,
  findRelevantArtifacts,
  findMostSimilarArtifact,
  formatArtifactsForContext,
  updateArtifactEmbedding,
} from './artifact-matcher';
export { artifactAgent, processWorkflowOutput } from './artifact-agent';
