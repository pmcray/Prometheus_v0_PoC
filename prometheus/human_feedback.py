
def get_human_preference(trajectory1, trajectory2):
    """
    Asks the user for their preference between two trajectories.

    Args:
        trajectory1: The first trajectory.
        trajectory2: The second trajectory.

    Returns:
        1 if trajectory1 is preferred, 2 if trajectory2 is preferred.
    """
    print("Please choose your preferred trajectory:")
    print("1: ", trajectory1)
    print("2: ", trajectory2)
    
    while True:
        try:
            choice = int(input("Enter 1 or 2: "))
            if choice in [1, 2]:
                return choice
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except ValueError:
            print("Invalid input. Please enter a number.")
