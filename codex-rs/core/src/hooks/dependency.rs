//! Hook dependency management and execution ordering.

use std::collections::{HashMap, HashSet, VecDeque};
use std::sync::Arc;

use crate::hooks::config::HookConfig;
use crate::hooks::types::{HookError, LifecycleEventType};

/// Dependency graph for hook execution ordering.
#[derive(Debug, Clone)]
pub struct DependencyGraph {
    /// Map of hook ID to hook configuration.
    hooks: HashMap<String, Arc<HookConfig>>,
    /// Map of hook ID to its dependencies.
    dependencies: HashMap<String, Vec<String>>,
    /// Map of hook ID to hooks that depend on it.
    dependents: HashMap<String, Vec<String>>,
}

impl DependencyGraph {
    /// Create a new dependency graph.
    pub fn new() -> Self {
        Self {
            hooks: HashMap::new(),
            dependencies: HashMap::new(),
            dependents: HashMap::new(),
        }
    }

    /// Add a hook to the dependency graph.
    pub fn add_hook(&mut self, mut hook: HookConfig) -> Result<(), HookError> {
        // Ensure the hook has an ID
        hook.ensure_id();
        let hook_id = hook.get_id();

        // Validate that dependencies don't create cycles
        self.validate_no_cycles(&hook_id, &hook.depends_on)?;

        // Store the hook
        let hook_arc = Arc::new(hook.clone());
        self.hooks.insert(hook_id.clone(), hook_arc);

        // Update dependency mappings
        self.dependencies.insert(hook_id.clone(), hook.depends_on.clone());

        // Update dependents mapping
        for dep_id in &hook.depends_on {
            self.dependents
                .entry(dep_id.clone())
                .or_insert_with(Vec::new)
                .push(hook_id.clone());
        }

        Ok(())
    }

    /// Get hooks for a specific event type, ordered by dependencies and priority.
    pub fn get_ordered_hooks(&self, event_type: LifecycleEventType) -> Result<Vec<Vec<Arc<HookConfig>>>, HookError> {
        // Filter hooks by event type
        let event_hooks: Vec<_> = self.hooks
            .values()
            .filter(|hook| hook.event == event_type)
            .cloned()
            .collect();

        if event_hooks.is_empty() {
            return Ok(vec![]);
        }

        // Perform topological sort to resolve dependencies
        let execution_order = self.topological_sort(&event_hooks)?;

        Ok(execution_order)
    }

    /// Perform topological sort to determine execution order.
    fn topological_sort(&self, hooks: &[Arc<HookConfig>]) -> Result<Vec<Vec<Arc<HookConfig>>>, HookError> {
        let mut result = Vec::new();
        let mut in_degree = HashMap::new();
        let mut hook_map = HashMap::new();

        // Build hook map and calculate in-degrees
        for hook in hooks {
            let hook_id = hook.get_id();
            hook_map.insert(hook_id.clone(), hook.clone());
            
            // Count dependencies that are in our current hook set
            let deps_in_set = hook.depends_on
                .iter()
                .filter(|dep_id| hooks.iter().any(|h| h.get_id() == **dep_id))
                .count();
            
            in_degree.insert(hook_id, deps_in_set);
        }

        // Process hooks level by level
        while !hook_map.is_empty() {
            // Find hooks with no remaining dependencies
            let ready_hooks: Vec<_> = in_degree
                .iter()
                .filter(|(_, &degree)| degree == 0)
                .map(|(hook_id, _)| hook_id.clone())
                .collect();

            if ready_hooks.is_empty() {
                return Err(HookError::Configuration(
                    "Circular dependency detected in hooks".to_string(),
                ));
            }

            // Group ready hooks by priority and parallel capability
            let mut current_level = Vec::new();
            let mut parallel_group = Vec::new();
            let mut sequential_hooks = Vec::new();

            for hook_id in ready_hooks {
                if let Some(hook) = hook_map.remove(&hook_id) {
                    in_degree.remove(&hook_id);

                    if hook.parallel {
                        parallel_group.push(hook);
                    } else {
                        sequential_hooks.push(hook);
                    }

                    // Update in-degrees of dependent hooks
                    if let Some(dependents) = self.dependents.get(&hook_id) {
                        for dependent_id in dependents {
                            if let Some(degree) = in_degree.get_mut(dependent_id) {
                                *degree = degree.saturating_sub(1);
                            }
                        }
                    }
                }
            }

            // Sort parallel hooks by priority
            parallel_group.sort_by_key(|hook| hook.priority);
            
            // Add parallel group as a single execution level
            if !parallel_group.is_empty() {
                current_level.push(parallel_group);
            }

            // Sort sequential hooks by priority and add each as separate level
            sequential_hooks.sort_by_key(|hook| hook.priority);
            for hook in sequential_hooks {
                current_level.push(vec![hook]);
            }

            // Add all levels from this iteration
            result.extend(current_level);
        }

        Ok(result)
    }

    /// Validate that adding dependencies won't create cycles.
    fn validate_no_cycles(&self, hook_id: &str, new_deps: &[String]) -> Result<(), HookError> {
        // Check if any of the new dependencies would create a cycle
        for dep_id in new_deps {
            if self.would_create_cycle(hook_id, dep_id)? {
                return Err(HookError::Configuration(format!(
                    "Adding dependency '{}' to hook '{}' would create a circular dependency",
                    dep_id, hook_id
                )));
            }
        }
        Ok(())
    }

    /// Check if adding a dependency would create a cycle.
    fn would_create_cycle(&self, from_hook: &str, to_hook: &str) -> Result<bool, HookError> {
        // If to_hook depends on from_hook (directly or indirectly), adding this dependency would create a cycle
        self.has_path(to_hook, from_hook)
    }

    /// Check if there's a dependency path from start to end.
    fn has_path(&self, start: &str, end: &str) -> Result<bool, HookError> {
        if start == end {
            return Ok(true);
        }

        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        queue.push_back(start.to_string());

        while let Some(current) = queue.pop_front() {
            if visited.contains(&current) {
                continue;
            }
            visited.insert(current.clone());

            if let Some(deps) = self.dependencies.get(&current) {
                for dep in deps {
                    if dep == end {
                        return Ok(true);
                    }
                    if !visited.contains(dep) {
                        queue.push_back(dep.clone());
                    }
                }
            }
        }

        Ok(false)
    }

    /// Get all hooks that depend on the given hook.
    pub fn get_dependents(&self, hook_id: &str) -> Vec<String> {
        self.dependents
            .get(hook_id)
            .cloned()
            .unwrap_or_default()
    }

    /// Get all dependencies of the given hook.
    pub fn get_dependencies(&self, hook_id: &str) -> Vec<String> {
        self.dependencies
            .get(hook_id)
            .cloned()
            .unwrap_or_default()
    }

    /// Check if a hook exists in the graph.
    pub fn contains_hook(&self, hook_id: &str) -> bool {
        self.hooks.contains_key(hook_id)
    }

    /// Get a hook by ID.
    pub fn get_hook(&self, hook_id: &str) -> Option<Arc<HookConfig>> {
        self.hooks.get(hook_id).cloned()
    }

    /// Get all hook IDs in the graph.
    pub fn get_all_hook_ids(&self) -> Vec<String> {
        self.hooks.keys().cloned().collect()
    }

    /// Validate all dependencies exist.
    pub fn validate_dependencies(&self) -> Result<(), HookError> {
        for (hook_id, deps) in &self.dependencies {
            for dep_id in deps {
                if !self.hooks.contains_key(dep_id) {
                    return Err(HookError::Configuration(format!(
                        "Hook '{}' depends on non-existent hook '{}'",
                        hook_id, dep_id
                    )));
                }
            }
        }
        Ok(())
    }

    /// Get execution statistics.
    pub fn get_stats(&self) -> DependencyStats {
        let total_hooks = self.hooks.len();
        let hooks_with_deps = self.dependencies.values().filter(|deps| !deps.is_empty()).count();
        let max_depth = self.calculate_max_depth();
        
        DependencyStats {
            total_hooks,
            hooks_with_dependencies: hooks_with_deps,
            max_dependency_depth: max_depth,
        }
    }

    /// Calculate the maximum dependency depth.
    fn calculate_max_depth(&self) -> usize {
        let mut max_depth = 0;
        
        for hook_id in self.hooks.keys() {
            let depth = self.calculate_hook_depth(hook_id, &mut HashSet::new());
            max_depth = max_depth.max(depth);
        }
        
        max_depth
    }

    /// Calculate the dependency depth of a specific hook.
    fn calculate_hook_depth(&self, hook_id: &str, visited: &mut HashSet<String>) -> usize {
        if visited.contains(hook_id) {
            return 0; // Avoid infinite recursion
        }
        
        visited.insert(hook_id.to_string());
        
        let deps = self.dependencies.get(hook_id).cloned().unwrap_or_default();
        if deps.is_empty() {
            return 0;
        }
        
        let max_dep_depth = deps
            .iter()
            .map(|dep_id| self.calculate_hook_depth(dep_id, visited))
            .max()
            .unwrap_or(0);
        
        visited.remove(hook_id);
        max_dep_depth + 1
    }
}

impl Default for DependencyGraph {
    fn default() -> Self {
        Self::new()
    }
}

/// Statistics about the dependency graph.
#[derive(Debug, Clone)]
pub struct DependencyStats {
    pub total_hooks: usize,
    pub hooks_with_dependencies: usize,
    pub max_dependency_depth: usize,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hooks::types::{HookType, HookExecutionMode, HookPriority, LifecycleEventType};
    use std::collections::HashMap;
    use std::time::Duration;

    fn create_test_hook(id: &str, event: LifecycleEventType, depends_on: Vec<String>) -> HookConfig {
        HookConfig {
            id: Some(id.to_string()),
            event,
            hook_type: HookType::Script {
                command: vec!["echo".to_string(), "test".to_string()],
                cwd: None,
                environment: HashMap::new(),
                timeout: Some(Duration::from_secs(5)),
            },
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            condition: None,
            blocking: false,
            required: false,
            tags: Vec::new(),
            description: Some(format!("Test hook {}", id)),
            depends_on,
            parallel: true,
            max_retries: 0,
            timeout: Some(Duration::from_secs(10)),
        }
    }

    #[test]
    fn test_dependency_graph_creation() {
        let mut graph = DependencyGraph::new();
        
        let hook1 = create_test_hook("hook1", LifecycleEventType::SessionStart, vec![]);
        let hook2 = create_test_hook("hook2", LifecycleEventType::SessionStart, vec!["hook1".to_string()]);
        
        assert!(graph.add_hook(hook1).is_ok());
        assert!(graph.add_hook(hook2).is_ok());
        
        assert!(graph.contains_hook("hook1"));
        assert!(graph.contains_hook("hook2"));
    }

    #[test]
    fn test_circular_dependency_detection() {
        let mut graph = DependencyGraph::new();
        
        let hook1 = create_test_hook("hook1", LifecycleEventType::SessionStart, vec!["hook2".to_string()]);
        let hook2 = create_test_hook("hook2", LifecycleEventType::SessionStart, vec!["hook1".to_string()]);
        
        assert!(graph.add_hook(hook1).is_ok());
        assert!(graph.add_hook(hook2).is_err()); // Should detect circular dependency
    }

    #[test]
    fn test_topological_sort() {
        let mut graph = DependencyGraph::new();
        
        let hook1 = create_test_hook("hook1", LifecycleEventType::SessionStart, vec![]);
        let hook2 = create_test_hook("hook2", LifecycleEventType::SessionStart, vec!["hook1".to_string()]);
        let hook3 = create_test_hook("hook3", LifecycleEventType::SessionStart, vec!["hook1".to_string()]);
        
        graph.add_hook(hook1).unwrap();
        graph.add_hook(hook2).unwrap();
        graph.add_hook(hook3).unwrap();
        
        let ordered = graph.get_ordered_hooks(LifecycleEventType::SessionStart).unwrap();
        
        // hook1 should be in the first level
        assert_eq!(ordered[0].len(), 1);
        assert_eq!(ordered[0][0].get_id(), "hook1");
        
        // hook2 and hook3 should be in the second level (can run in parallel)
        assert_eq!(ordered[1].len(), 2);
        let second_level_ids: Vec<_> = ordered[1].iter().map(|h| h.get_id()).collect();
        assert!(second_level_ids.contains(&"hook2".to_string()));
        assert!(second_level_ids.contains(&"hook3".to_string()));
    }

    #[test]
    fn test_dependency_validation() {
        let mut graph = DependencyGraph::new();
        
        let hook1 = create_test_hook("hook1", LifecycleEventType::SessionStart, vec![]);
        let hook2 = create_test_hook("hook2", LifecycleEventType::SessionStart, vec!["nonexistent".to_string()]);
        
        graph.add_hook(hook1).unwrap();
        graph.add_hook(hook2).unwrap();
        
        // Should fail validation because "nonexistent" hook doesn't exist
        assert!(graph.validate_dependencies().is_err());
    }

    #[test]
    fn test_sequential_vs_parallel_execution() {
        let mut graph = DependencyGraph::new();
        
        let mut hook1 = create_test_hook("hook1", LifecycleEventType::SessionStart, vec![]);
        hook1.parallel = false; // Sequential
        
        let hook2 = create_test_hook("hook2", LifecycleEventType::SessionStart, vec![]);
        // hook2.parallel = true (default)
        
        let hook3 = create_test_hook("hook3", LifecycleEventType::SessionStart, vec![]);
        // hook3.parallel = true (default)
        
        graph.add_hook(hook1).unwrap();
        graph.add_hook(hook2).unwrap();
        graph.add_hook(hook3).unwrap();
        
        let ordered = graph.get_ordered_hooks(LifecycleEventType::SessionStart).unwrap();
        
        // Should have multiple levels due to sequential hook
        assert!(ordered.len() >= 2);
    }

    #[test]
    fn test_dependency_stats() {
        let mut graph = DependencyGraph::new();
        
        let hook1 = create_test_hook("hook1", LifecycleEventType::SessionStart, vec![]);
        let hook2 = create_test_hook("hook2", LifecycleEventType::SessionStart, vec!["hook1".to_string()]);
        let hook3 = create_test_hook("hook3", LifecycleEventType::SessionStart, vec!["hook2".to_string()]);
        
        graph.add_hook(hook1).unwrap();
        graph.add_hook(hook2).unwrap();
        graph.add_hook(hook3).unwrap();
        
        let stats = graph.get_stats();
        assert_eq!(stats.total_hooks, 3);
        assert_eq!(stats.hooks_with_dependencies, 2);
        assert_eq!(stats.max_dependency_depth, 2);
    }
}
