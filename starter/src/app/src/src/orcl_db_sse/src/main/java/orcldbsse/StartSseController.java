package orcldbsse;

import io.micronaut.http.HttpResponse;
import io.micronaut.http.MediaType;
import io.micronaut.http.annotation.*;

import jakarta.inject.Inject;

@Controller
public class StartSseController { 

  @Inject
  SseIngestService sseIngestService; 

  @Post(uri = "/startsse", consumes = MediaType.APPLICATION_JSON)
  public HttpResponse<String> start(@Body StartSseRequest body) {
    sseIngestService.startAndIngest(body);
    return HttpResponse.ok("SSE started");
  }
}