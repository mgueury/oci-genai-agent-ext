package orcldbsee;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpStatus;
import reactor.core.publisher.Mono;

@RestController
public class SseController {
    private final SseIngestService service;

    public SseController(SseIngestService service) {
        this.service = service;
    }

    // Example: POST /async_sse?thread_id=abc123
    @PostMapping(path = "/async")
    public ResponseEntity<String> async(@RequestParam("thread_id") String threadId,
            @RequestBody String jsonBody) {

        service.start(threadId, jsonBody).subscribe(); // Fire and forget
        return ResponseEntity.accepted().body("SSE call started for thread_id=" + threadId);
    }

    @PostMapping(path = "/sync")
    public Mono<ResponseEntity<String>> startSse(@RequestParam("thread_id") String threadId,
            @RequestBody String jsonBody) {
        return service.start(threadId, jsonBody).then()
                // We immediately return Accepted to indicate the ingestion has started
                // asynchronously
                .thenReturn(ResponseEntity.status(HttpStatus.ACCEPTED)
                        .body("SSE ingestion finished for thread_id=" + threadId));
    }
}

