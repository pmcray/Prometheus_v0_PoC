import cProfile
import pstats
import main
from memory_profiler import profile

# Add the @profile decorator to the main function for memory profiling
main.main = profile(main.main)

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    main.main()

    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats()
    stats.dump_stats('application_profile.pstat')
