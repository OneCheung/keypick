/**
 * KeyPick Cloudflare Workers Gateway
 *
 * This worker acts as an API gateway for KeyPick, providing:
 * - Global CDN distribution
 * - API key authentication
 * - Request routing
 * - Response caching
 * - Rate limiting
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, Authorization',
      'Access-Control-Max-Age': '86400',
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      // Health check endpoint (cached at edge)
      if (url.pathname === '/' || url.pathname === '/health') {
        return new Response(JSON.stringify({
          status: 'healthy',
          service: 'KeyPick API Gateway',
          timestamp: new Date().toISOString(),
          region: request.cf?.colo || 'unknown'
        }), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=60',
            ...corsHeaders
          }
        });
      }

      // API version endpoint
      if (url.pathname === '/api/version') {
        return new Response(JSON.stringify({
          version: '0.1.0',
          api: 'KeyPick',
          gateway: 'Cloudflare Workers'
        }), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=3600',
            ...corsHeaders
          }
        });
      }

      // Check API key for protected endpoints
      if (url.pathname.startsWith('/api/')) {
        const apiKey = request.headers.get('X-API-Key') ||
                      request.headers.get('Authorization')?.replace('Bearer ', '');

        if (!apiKey) {
          return new Response(JSON.stringify({
            error: 'API key required',
            message: 'Please provide X-API-Key header or Authorization Bearer token'
          }), {
            status: 401,
            headers: {
              'Content-Type': 'application/json',
              ...corsHeaders
            }
          });
        }

        // Validate API key
        const validKeys = env.KEYPICK_API_KEYS?.split(',') || [];
        if (!validKeys.includes(apiKey)) {
          // Rate limit invalid attempts
          const ip = request.headers.get('CF-Connecting-IP');
          const rateLimitKey = `ratelimit:${ip}`;
          const attempts = await env.CACHE.get(rateLimitKey) || 0;

          if (attempts > 10) {
            return new Response(JSON.stringify({
              error: 'Too many failed attempts',
              message: 'Please try again later'
            }), {
              status: 429,
              headers: {
                'Content-Type': 'application/json',
                'Retry-After': '3600',
                ...corsHeaders
              }
            });
          }

          await env.CACHE.put(rateLimitKey, parseInt(attempts) + 1, {
            expirationTtl: 3600
          });

          return new Response(JSON.stringify({
            error: 'Invalid API key',
            message: 'The provided API key is not valid'
          }), {
            status: 401,
            headers: {
              'Content-Type': 'application/json',
              ...corsHeaders
            }
          });
        }
      }

      // Handle crawl task creation with queue
      if (url.pathname === '/api/crawl/' && request.method === 'POST') {
        const body = await request.json();
        const taskId = crypto.randomUUID();

        // Validate request
        if (!body.platform || !body.keywords) {
          return new Response(JSON.stringify({
            error: 'Invalid request',
            message: 'platform and keywords are required'
          }), {
            status: 400,
            headers: {
              'Content-Type': 'application/json',
              ...corsHeaders
            }
          });
        }

        // Send to queue for async processing
        if (env.CRAWLER_QUEUE) {
          await env.CRAWLER_QUEUE.send({
            taskId,
            platform: body.platform,
            keywords: body.keywords,
            max_results: body.max_results || 10,
            timestamp: Date.now()
          });
        }

        // Store task metadata in KV
        await env.CACHE.put(`task:${taskId}`, JSON.stringify({
          status: 'pending',
          platform: body.platform,
          keywords: body.keywords,
          created_at: new Date().toISOString()
        }), {
          expirationTtl: 86400 // 24 hours
        });

        // Return task ID immediately
        return new Response(JSON.stringify({
          task_id: taskId,
          status: 'pending',
          message: 'Task queued for processing',
          check_status_at: `/api/crawl/status/${taskId}`
        }), {
          status: 202,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }

      // Check task status from cache
      if (url.pathname.match(/^\/api\/crawl\/status\/[\w-]+$/)) {
        const taskId = url.pathname.split('/').pop();
        const taskData = await env.CACHE.get(`task:${taskId}`);

        if (!taskData) {
          // Fallback to backend
          const backendUrl = `${env.BACKEND_URL}${url.pathname}`;
          const response = await fetch(backendUrl, {
            headers: {
              'X-Internal-Key': env.INTERNAL_KEY
            }
          });

          return new Response(await response.text(), {
            status: response.status,
            headers: {
              'Content-Type': 'application/json',
              ...corsHeaders
            }
          });
        }

        return new Response(taskData, {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'private, max-age=5',
            ...corsHeaders
          }
        });
      }

      // Cache platform list
      if (url.pathname === '/api/crawl/platforms' && request.method === 'GET') {
        const cacheKey = 'platforms:list';
        const cached = await env.CACHE.get(cacheKey);

        if (cached) {
          return new Response(cached, {
            status: 200,
            headers: {
              'Content-Type': 'application/json',
              'X-Cache': 'HIT',
              'Cache-Control': 'public, max-age=3600',
              ...corsHeaders
            }
          });
        }

        // Fetch from backend
        const backendUrl = `${env.BACKEND_URL}${url.pathname}`;
        const response = await fetch(backendUrl);
        const data = await response.text();

        // Cache the response
        await env.CACHE.put(cacheKey, data, {
          expirationTtl: 3600
        });

        return new Response(data, {
          status: response.status,
          headers: {
            'Content-Type': 'application/json',
            'X-Cache': 'MISS',
            ...corsHeaders
          }
        });
      }

      // Forward all other requests to backend
      const backendUrl = `${env.BACKEND_URL}${url.pathname}${url.search}`;

      // Clone request and add internal auth
      const backendHeaders = new Headers(request.headers);
      backendHeaders.set('X-Internal-Key', env.INTERNAL_KEY);
      backendHeaders.set('X-Forwarded-For', request.headers.get('CF-Connecting-IP'));
      backendHeaders.set('X-Real-IP', request.headers.get('CF-Connecting-IP'));

      const backendRequest = new Request(backendUrl, {
        method: request.method,
        headers: backendHeaders,
        body: request.body,
        redirect: 'follow'
      });

      const response = await fetch(backendRequest);

      // Add CORS headers to response
      const responseHeaders = new Headers(response.headers);
      Object.keys(corsHeaders).forEach(key => {
        responseHeaders.set(key, corsHeaders[key]);
      });

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders
      });

    } catch (error) {
      console.error('Worker error:', error);

      return new Response(JSON.stringify({
        error: 'Internal server error',
        message: 'An unexpected error occurred',
        details: error.message
      }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    }
  },

  // Queue consumer for async tasks
  async queue(batch, env) {
    for (const message of batch.messages) {
      try {
        const { taskId, platform, keywords, max_results } = message.body;

        // Call backend to process crawl
        const response = await fetch(`${env.BACKEND_URL}/api/crawl/execute`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Internal-Key': env.INTERNAL_KEY
          },
          body: JSON.stringify({
            task_id: taskId,
            platform,
            keywords,
            max_results
          })
        });

        if (response.ok) {
          // Update task status in cache
          const result = await response.json();
          await env.CACHE.put(`task:${taskId}`, JSON.stringify({
            status: 'completed',
            result: result,
            completed_at: new Date().toISOString()
          }), {
            expirationTtl: 86400
          });

          message.ack();
        } else {
          console.error(`Task ${taskId} failed:`, await response.text());
          message.retry();
        }
      } catch (error) {
        console.error('Queue processing error:', error);
        message.retry();
      }
    }
  }
};